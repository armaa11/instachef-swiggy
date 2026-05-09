"""
Instagram Reels extractor — Custom pure Python scraper + RapidAPI fallback.
Unlike competitors relying on Apify, we use a lightweight custom architecture.
"""
import re
import httpx
import structlog
import json
from app.config import settings

logger = structlog.get_logger()

async def extract_instagram(url: str) -> tuple[str, str]:
    """
    Extract recipe content from an Instagram Reel URL.
    Uses public scraping with headers as primary, RapidAPI as fallback.
    """
    reel_id = _extract_reel_id(url)
    if not reel_id:
        raise Exception("Invalid Instagram URL — could not extract reel/post ID.")

    # ── Strategy 1: Native Public Page Scraping ─────────
    try:
        content = await _scrape_public_page(url)
        if content and len(content.strip()) > 20:
            logger.info("instagram.public_scrape_success", reel_id=reel_id, content_length=len(content))
            return content, "native_scrape"
    except Exception as e:
        logger.warning("instagram.public_scrape_failed", error=str(e)[:100])

    # ── Strategy 2: RapidAPI Fallback (if configured) ───
    rapid_key = getattr(settings, "RAPIDAPI_KEY", None)
    if rapid_key:
        try:
            content = await _scrape_rapidapi(url, rapid_key)
            if content and len(content.strip()) > 20:
                logger.info("instagram.rapidapi_success", reel_id=reel_id, content_length=len(content))
                return content, "rapidapi"
        except Exception as e:
            logger.warning("instagram.rapidapi_failed", error=str(e)[:100])

    raise Exception(
        f"Could not extract content from Instagram reel {reel_id}. "
        f"Try pasting the recipe caption or ingredients directly."
    )

def _extract_reel_id(url: str) -> str | None:
    patterns = [
        r"instagram\.com/reel/([A-Za-z0-9_-]+)",
        r"instagram\.com/reels/([A-Za-z0-9_-]+)",
        r"instagram\.com/p/([A-Za-z0-9_-]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def _scrape_public_page(url: str) -> str:
    """Scrape the public Instagram page for og:description and JSON-LD data."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        response = await client.get(url, headers=headers)
        html = response.text

    parts = []
    
    # Extract og:description
    og_match = re.search(r'<meta\s+(?:property|name)="og:description"\s+content="([^"]*)"', html, re.IGNORECASE)
    if og_match:
        parts.append(og_match.group(1))

    # Extract JSON-LD
    ld_matches = re.findall(r'<script type="application/ld\+json">(.+?)</script>', html, re.DOTALL)
    for ld_text in ld_matches:
        try:
            ld = json.loads(ld_text)
            if isinstance(ld, dict):
                for key in ["caption", "description", "articleBody", "text"]:
                    if ld.get(key):
                        parts.append(ld[key])
        except json.JSONDecodeError:
            pass

    return "\n\n".join(parts) if parts else ""

async def _scrape_rapidapi(url: str, api_key: str) -> str:
    """Fallback using a generic RapidAPI Instagram scraper endpoint."""
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "instagram-scraper-api2.p.rapidapi.com"
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(
            "https://instagram-scraper-api2.p.rapidapi.com/v1/post_info",
            params={"code_or_id_or_url": url},
            headers=headers
        )
        data = response.json()
        caption = data.get("data", {}).get("caption", {}).get("text", "")
        return caption
