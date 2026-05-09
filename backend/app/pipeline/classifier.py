def classify_input(url_or_text: str) -> str:
    url_or_text = url_or_text.lower()
    if "youtube.com" in url_or_text or "youtu.be" in url_or_text:
        return "youtube"
    elif "instagram.com" in url_or_text:
        return "instagram"
    elif url_or_text.startswith("http"):
        return "blog"
    return "text"
