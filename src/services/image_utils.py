import os
from io import BytesIO
from typing import Optional

from PIL import Image as PILImage


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
