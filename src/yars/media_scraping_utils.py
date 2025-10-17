import re

def extract_media_id_from_url(url: str) -> str | None:
    """Try to extract a Reddit-style media_id from a URL."""
    match = re.search(r"(?:preview|i)\.redd\.it/([a-zA-Z0-9]+)", url)
    if match:
        return match.group(1)
    return None

def extract_media_file_extension_from_url(url: str) -> str | None:
    """Extract file extension from a URL if present."""
    match = re.search(r"\.(jpg|jpeg|png|gif|webp|mp4|mov)(?:\?|$)", url, re.IGNORECASE)
    if match:
        return match.group(1).lower()
    return None


def extract_gallery_media(data, meta):
    """Extract all images/videos from a Reddit gallery post."""
    results = []
    if not (data.get("is_gallery") and "media_metadata" in data):
        return results

    media_metadata = data["media_metadata"]
    gallery_data = data.get("gallery_data", {}) or {}
    gallery_items = gallery_data.get("items", [])
    for item in gallery_items:
        media_id = item.get("media_id")
        meta_info = media_metadata.get(media_id)
        if not meta_info:
            continue

        media_type = meta_info.get("e")  # 'Image' or 'Video'
        source = meta_info.get("s", {})

        if media_type == "Image" and "u" in source:
            extension = extract_media_file_extension_from_url(source.get("u", ""))
            results.append({**meta, "type": "image", "url": source["u"], "media_id": media_id, "extension": extension})
        elif media_type == "Video":
            video_url = source.get("mp4") or source.get("u")
            if video_url:
                extension = extract_media_file_extension_from_url(video_url)
                results.append({**meta, "type": "video", "url": video_url, "media_id": media_id, "extension": extension})

    return results


def extract_single_image(data, meta):
    """Extract single image posts (non-gallery)."""
    url = data.get("url_overridden_by_dest", "")
    if url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        media_id = extract_media_id_from_url(url)
        extension = extract_media_file_extension_from_url(url)
        return [{**meta, "type": "image", "url": url, "media_id": media_id, "extension": extension}]
    return []


def extract_single_video(data, meta):
    """Extract Reddit-hosted video posts."""
    media = data.get("media") or data.get("secure_media")
    if not media:
        return []

    reddit_video = media.get("reddit_video")
    if reddit_video and "fallback_url" in reddit_video:
        url = reddit_video["fallback_url"]
        media_id = extract_media_id_from_url(url)
        extension = extract_media_file_extension_from_url(url)
        return [{**meta, "type": "video", "url": url, "media_id": media_id, "extension": extension}]
    return []


def extract_fallback_preview(data, meta):
    """Extract fallback image from preview if no other media."""
    preview = data.get("preview", {})
    images = preview.get("images", [])
    if images:
        source = images[0].get("source", {})
        if "url" in source:
            url = source["url"]
            media_id = extract_media_id_from_url(url)
            extension = extract_media_file_extension_from_url(url)
            return [{**meta, "type": "image", "url": url, "media_id": media_id, "extension": extension}]
    return []


def extract_reddit_media(post_json):
    """
    Extract all high-res media URLs + metadata from a single Reddit post JSON.
    Includes:
      - Galleries
      - Single images
      - Videos
      - Fallback previews
    Returns a list of dicts:
      [{"type": "image", "url": ..., "media_id": ..., "title": ..., ...}]
    """
    data = post_json.get("data", {})

    meta = {
        "title": data.get("title", ""),
        "permalink": f"https://www.reddit.com{data.get('permalink', '')}",
        "subreddit": data.get("subreddit", ""),
        "author": data.get("author", ""),
        "id": data.get("id", ""),
    }

    results = []
    extractors = [
        extract_gallery_media,
        extract_single_image,
        extract_single_video,
        extract_fallback_preview,
    ]

    for extractor in extractors:
        media_items = extractor(data, meta)
        if media_items:
            results.extend(media_items)

    return results


def extract_from_listing(listing):
    """
    Extract all media + metadata from a Reddit listing (e.g. r/subreddit/new.json).
    Returns a list of dicts.
    """
    results = []

    for child in listing:
        if child.get("kind") == "t3":  # post
            results.extend(extract_reddit_media(child))

    return results



