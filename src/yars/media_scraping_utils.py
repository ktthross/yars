def extract_gallery_media(data, meta):
    """Extract all images/videos from a Reddit gallery post."""
    results = []
    if not (data.get("is_gallery") and "media_metadata" in data):
        return results

    media_metadata = data["media_metadata"]
    gallery_items = data.get("gallery_data", {}).get("items", [])
    for item in gallery_items:
        media_id = item.get("media_id")
        meta_info = media_metadata.get(media_id)
        if not meta_info:
            continue

        media_type = meta_info.get("e")  # 'Image' or 'Video'
        source = meta_info.get("s", {})

        if media_type == "Image" and "u" in source:
            results.append({**meta, "type": "image", "url": source["u"]})
        elif media_type == "Video":
            video_url = source.get("mp4") or source.get("u")
            if video_url:
                results.append({**meta, "type": "video", "url": video_url})

    return results


def extract_single_image(data, meta):
    """Extract single image posts (non-gallery)."""
    url = data.get("url_overridden_by_dest", "")
    if url.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return [{**meta, "type": "image", "url": url}]
    return []


def extract_single_video(data, meta):
    """Extract Reddit-hosted video posts."""
    media = data.get("media") or data.get("secure_media")
    if not media:
        return []

    reddit_video = media.get("reddit_video")
    if reddit_video and "fallback_url" in reddit_video:
        return [{**meta, "type": "video", "url": reddit_video["fallback_url"]}]
    return []


def extract_fallback_preview(data, meta):
    """Extract fallback image from preview if no other media."""
    preview = data.get("preview", {})
    images = preview.get("images", [])
    if images:
        source = images[0].get("source", {})
        if "url" in source:
            return [{**meta, "type": "image", "url": source["url"]}]
    return []


def extract_reddit_media(post_json):
    """
    Extract all high-res media URLs + metadata from a single Reddit post JSON.
    """
    data = post_json.get("data", {})

    meta = {
        "title": data.get("title", ""),
        "permalink": f"https://www.reddit.com{data.get('permalink', '')}",
        "subreddit": data.get("subreddit", ""),
        "author": data.get("author", ""),
        "id": data.get("id", "")
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


def extract_from_listing(listing_json):
    """
    Extract all media + metadata from a Reddit listing (e.g. r/subreddit/new.json).
    Returns a list of dicts.
    """
    results = []
    children = listing_json.get("data", {}).get("children", [])

    for child in children:
        if child.get("kind") == "t3":  # post
            results.extend(extract_reddit_media(child))

    return results
