import hashlib
import logging
import os
import tempfile
from io import BytesIO
from typing import Optional

import requests
from PIL import Image as PILImage

logger = logging.getLogger(__name__)

# Cache directory for downloaded Catsy images
_IMAGE_CACHE_DIR = os.path.join(tempfile.gettempdir(), "bin_label_maker_images")


def load_image(path: Optional[str]) -> Optional[PILImage.Image]:
    """Load an image from disk, returning None if path is invalid."""
    if not path or not os.path.isfile(path):
        return None
    try:
        img = PILImage.open(path)
        img.load()
        return img
    except Exception:
        return None


def download_image(url: str) -> Optional[str]:
    """Download an image from a URL and cache it locally.

    Returns the local file path, or None on failure.
    """
    if not url:
        return None

    os.makedirs(_IMAGE_CACHE_DIR, exist_ok=True)

    # Use URL hash as filename to avoid re-downloading
    url_hash = hashlib.md5(url.encode()).hexdigest()
    ext = ".jpg"
    if ".png" in url.lower():
        ext = ".png"
    elif ".gif" in url.lower():
        ext = ".gif"
    cache_path = os.path.join(_IMAGE_CACHE_DIR, f"{url_hash}{ext}")

    if os.path.isfile(cache_path):
        return cache_path

    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        with open(cache_path, "wb") as f:
            f.write(resp.content)
        return cache_path
    except Exception as e:
        logger.warning("Failed to download image %s: %s", url, e)
        return None


def scale_image_to_fit(
    image: PILImage.Image, max_width: int, max_height: int
) -> PILImage.Image:
    """Scale image to fit within bounds, preserving aspect ratio."""
    w, h = image.size
    if w == 0 or h == 0:
        return image
    ratio = min(max_width / w, max_height / h)
    if ratio >= 1.0:
        return image
    new_w = max(1, int(w * ratio))
    new_h = max(1, int(h * ratio))
    return image.resize((new_w, new_h), PILImage.Resampling.LANCZOS)


def image_to_bytes(image: PILImage.Image, fmt: str = "PNG") -> bytes:
    """Convert a PIL Image to bytes."""
    buf = BytesIO()
    image.save(buf, format=fmt)
    return buf.getvalue()
