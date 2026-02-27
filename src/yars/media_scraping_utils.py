import re
import requests

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
        if media_metadata is None or media_id is None:
            continue
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


def extract_redgifs_id_from_url(url: str) -> str | None:
    """Extract a RedGIFs id from common RedGIFs URLs or embed HTML."""
    if not url:
        return None
    # common patterns: https://www.redgifs.com/watch/ID or https://www.redgifs.com/ifr/ID
    match = re.search(r"redgifs\.com/(?:watch|ifr)/([A-Za-z0-9_-]+)", url)
    if match:
        return match.group(1)
    # media.redgifs.com/Name-poster.jpg -> capture Name
    match = re.search(r"/([A-Za-z0-9]+)-poster\.", url)
    if match:
        return match.group(1)
    return None


def _find_first_mp4(obj):
    """Recursively search a JSON-like object for the first .mp4 URL string."""
    if isinstance(obj, str):
        if obj.lower().endswith(".mp4"):
            return obj
        # sometimes URLs contain query params
        if ".mp4?" in obj.lower():
            return obj.split('.mp4')[0] + '.mp4'
        return None
    if isinstance(obj, dict):
        for v in obj.values():
            found = _find_first_mp4(v)
            if found:
                return found
    if isinstance(obj, list):
        for v in obj:
            found = _find_first_mp4(v)
            if found:
                return found
    return None


def get_redgifs_mp4_url(red_id: str) -> str | None:
    """Try to resolve a RedGIFs id to a direct MP4 URL using the RedGIFs public API.

    Returns the MP4 URL on success, otherwise None.
    """
    if not red_id:
        return None

    api_url = f"https://api.redgifs.com/v2/gifs/{red_id}"
    try:
        resp = requests.get(api_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        mp4 = _find_first_mp4(data)
        if mp4:
            return mp4
    except Exception:
        # If API lookup fails, try a best-effort CDN guess (may not always work).
        pass

    # Best-effort fallback: try common CDN patterns used by RedGIFs
    # pattern: https://thumbs2.redgifs.com/<slug>-mobile.mp4 or <slug>.mp4
    candidates = [
        f"https://thumbs2.redgifs.com/{red_id}.mp4",
        f"https://thumbs2.redgifs.com/{red_id}-mobile.mp4",
        f"https://thumbs1.redgifs.com/{red_id}.mp4",
    ]
    for c in candidates:
        try:
            r = requests.head(c, timeout=3)
            if r.status_code == 200:
                return c
        except Exception:
            continue
    return None


def extract_redgifs_media(data, meta):
    """Detect and extract RedGIFs media when present. Prefers RedGIFs embed/watch URLs.

    Returns a list with a single video dict when RedGIFs content is detected, otherwise []
    """
    results = []
    if not data:
        return results

    domain = (data.get("domain") or "").lower()
    url = data.get("url_overridden_by_dest", "") or ""
    media = data.get("media") or {}
    secure_media = data.get("secure_media") or {}
    media_embed = data.get("media_embed") or {}

    # oembed may be nested under secure_media or media
    oembed = {}
    if isinstance(secure_media, dict):
        oembed = secure_media.get("oembed") or {}
    if not oembed and isinstance(media, dict):
        oembed = media.get("oembed") or {}

    content_html = media_embed.get("content", "") or oembed.get("html", "") or ""

    detected = False
    if "redgifs" in domain or "redgifs.com" in url or "redgifs.com" in content_html:
        detected = True
    if secure_media.get("type") == "redgifs.com":
        detected = True
    if oembed.get("provider_name") and "redgif" in oembed.get("provider_name", "").lower():
        detected = True

    if not detected:
        return results

    # Try to find a RedGIFs id
    red_id = extract_redgifs_id_from_url(url) or extract_redgifs_id_from_url(content_html) or extract_redgifs_id_from_url(oembed.get("thumbnail_url", ""))

    # We only include the RedGIFs id in the metadata here.  Resolution to a
    # direct MP4 URL is performed by the downloader using the id. This avoids
    # storing or propagating full RedGIFs embed/watch URLs in the metadata.
    if not red_id:
        return results

    # Use a sensible default extension for RedGIFs media; downloader may
    # override by resolving the actual MP4 URL later.
    extension = "mp4"

    # Include a dedicated `redgifs_id` so callers can detect RedGIFs posts
    # and use the RedGIFs-specific downloader. Keep `media_id` for compatibility.
    item = {
        **meta,
        "type": "video",
        "url": None,
        "media_id": red_id,
        "redgifs_id": red_id,
        "extension": extension,
        "provider": "redgifs",
    }
    results.append(item)
    return results


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
        extract_redgifs_media,
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



