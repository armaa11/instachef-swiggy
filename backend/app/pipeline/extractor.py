import hashlib
import sys
import os
import structlog
from redis import Redis
from youtube_transcript_api import YouTubeTranscriptApi
from recipe_scrapers import scrape_me
import trafilatura
from app.config import settings
import urllib.parse as urlparse

logger = structlog.get_logger()

redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)

CACHE_TTL = 86400  # 24 hours — no reason to re-fetch the same content


def get_video_id(url):
    url_data = urlparse.urlparse(url)
    query = urlparse.parse_qs(url_data.query)
    if "v" in query:
        return query["v"][0]
    elif "youtu.be" in url_data.netloc:
        return url_data.path.lstrip("/")
    return None


def _get_yt_dlp_path() -> str:
    venv_scripts = os.path.join(os.path.dirname(sys.executable))
    candidates = [
        os.path.join(venv_scripts, "yt-dlp.exe"),
        os.path.join(venv_scripts, "yt-dlp"),
        "yt-dlp",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return "yt-dlp"

async def _get_youtube_metadata(url: str) -> str:
    """Fetch video title and description using yt-dlp."""
    try:
        import subprocess
        yt_dlp_bin = _get_yt_dlp_path()
        # Use --print to get title and description in one go
        result = subprocess.run(
            [yt_dlp_bin, "--print", "title", "--print", "description", "--no-playlist", url],
            check=True, capture_output=True, text=True, timeout=10, encoding='utf-8'
        )
        return result.stdout.strip()
    except Exception as e:
        logger.warning("extract.youtube.metadata_failed", error=str(e))
        return ""


async def extract_content(url_or_text: str, input_type: str) -> tuple[str, str]:
    """
    Extract raw text content from a URL or plain text.
    Uses a 3-tier fallback for YouTube: subtitles → faster-whisper → OpenAI Whisper.
    Uses Apify 3-actor fallback for Instagram Reels.
    All results are cached in Redis for 24 hours.
    """
    cache_key = f"extract:{hashlib.sha256(url_or_text.encode()).hexdigest()}"
    cached = redis_client.get(cache_key)
    if cached:
        return cached, "cache"

    content = ""
    source = ""

    if input_type == "youtube":
        content, source = await _extract_youtube(url_or_text)
    elif input_type == "instagram":
        from app.pipeline.instagram import extract_instagram
        content, source = await extract_instagram(url_or_text)
    elif input_type == "blog":
        content, source = _extract_blog(url_or_text)
    else:
        content = url_or_text
        source = "text"

    if content:
        redis_client.setex(cache_key, CACHE_TTL, content)

    if not content:
        raise Exception("Could not extract any content from the provided input.")

    return content, source


async def _extract_youtube(url: str) -> tuple[str, str]:
    video_id = get_video_id(url)
    if not video_id:
        raise Exception("Invalid YouTube URL — could not extract video ID.")

    errors = []
    
    # Pre-fetch metadata (Description often contains the full ingredient list!)
    metadata = await _get_youtube_metadata(url)
    if metadata:
        logger.info("extract.youtube.metadata_fetched", video_id=video_id)

    # ── Tier 1: YouTube Transcript API (fastest, free) ────────────
    try:
        transcript_list = YouTubeTranscriptApi().fetch(
            video_id, languages=["en", "hi", "ta", "te", "kn", "mr"]
        )
        # In version 1.2.x, transcript_list is an Iterable of FetchedTranscriptSnippet objects, which have a .text attribute
        content = " ".join([snippet.text for snippet in transcript_list])
        if content.strip():
            final_content = f"VIDEO METADATA:\n{metadata}\n\nTRANSCRIPT:\n{content}"
            logger.info("extract.youtube.subtitles", video_id=video_id,
                         word_count=len(final_content.split()))
            return final_content, "subtitle_api"
    except Exception as e:
        errors.append(f"subtitle_api: {str(e)[:100]}")
        logger.info("extract.youtube.subtitles_failed", video_id=video_id,
                      error=str(e)[:100])

    # ── Fast Fallback: Use Metadata if Subtitles fail ─────────────
    # If we have a substantial description, use it and skip the slow local transcription.
    if metadata and len(metadata.strip().split()) > 20:
        logger.info("extract.youtube.using_metadata_fallback", video_id=video_id)
        return f"VIDEO METADATA (FALLBACK):\n{metadata}", "metadata_fallback"

    # ── Tier 2: yt-dlp + faster-whisper (local, free) ─────────────
    try:
        import subprocess
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            audio_path = os.path.join(tmpdir, "audio.m4a")
            yt_dlp_bin = _get_yt_dlp_path()

            logger.info("extract.youtube.ytdlp", binary=yt_dlp_bin)
            subprocess.run(
                [yt_dlp_bin, "-f", "bestaudio[ext=m4a]/bestaudio",
                 "--no-playlist", "-o", audio_path, url],
                check=True, capture_output=True, timeout=120,
            )

            from faster_whisper import WhisperModel
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, info = model.transcribe(audio_path, beam_size=5)
            content = " ".join([segment.text for segment in segments])

            if content.strip():
                final_content = f"VIDEO METADATA:\n{metadata}\n\nTRANSCRIPT:\n{content}"
                logger.info("extract.youtube.faster_whisper",
                             video_id=video_id, word_count=len(final_content.split()))
                return final_content, "faster_whisper"
    except Exception as e:
        errors.append(f"faster_whisper: {str(e)[:100]}")
        logger.info("extract.youtube.faster_whisper_failed",
                      video_id=video_id, error=str(e)[:100])

    # ── Tier 3: OpenAI Whisper API (paid, reliable) ───────────────
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your_openai_key_here":
        try:
            import subprocess
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                audio_path = os.path.join(tmpdir, "audio.m4a")
                yt_dlp_bin = _get_yt_dlp_path()

                # Only download if not already downloaded
                if not os.path.exists(audio_path):
                    subprocess.run(
                        [yt_dlp_bin, "-f", "bestaudio[ext=m4a]/bestaudio",
                         "--no-playlist", "-o", audio_path, url],
                        check=True, capture_output=True, timeout=120,
                    )

                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
                with open(audio_path, "rb") as audio_file:
                    transcription = await client.audio.transcriptions.create(
                        model="whisper-1", file=audio_file
                    )
                content = transcription.text
                if content.strip():
                    logger.info("extract.youtube.whisper_api",
                                 video_id=video_id, word_count=len(content.split()))
                    return content, "whisper_api"
        except Exception as e:
            errors.append(f"whisper_api: {str(e)[:100]}")
            logger.info("extract.youtube.whisper_api_failed",
                          video_id=video_id, error=str(e)[:100])

    # ── All tiers failed ──────────────────────────────────────────
    raise Exception(
        f"All transcription methods failed for video {video_id}. "
        f"Errors: {'; '.join(errors)}. "
        f"Try pasting the recipe text directly."
    )


def _extract_blog(url: str) -> tuple[str, str]:
    """Extract recipe from a blog URL. Tries structured scraper first, falls back to trafilatura."""
    try:
        scraper = scrape_me(url)
        content = (
            f"Title: {scraper.title()}\n"
            f"Ingredients: {', '.join(scraper.ingredients())}\n"
            f"Instructions: {scraper.instructions()}"
        )
        if content.strip():
            return content, "scraper"
    except Exception:
        pass

    try:
        downloaded = trafilatura.fetch_url(url)
        content = trafilatura.extract(downloaded) if downloaded else ""
        if content and content.strip():
            return content, "trafilatura"
    except Exception:
        pass

    raise Exception("Could not extract content from the provided blog URL.")
