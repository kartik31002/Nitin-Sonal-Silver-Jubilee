"""Image loading utilities — Pillow + HEIC + OpenCV interop."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except Exception:  # noqa: BLE001 - HEIC support is optional
    pass


def load_rgb(path: Path) -> np.ndarray:
    """Load an image as an RGB uint8 ndarray, respecting EXIF orientation."""

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return np.array(img, dtype=np.uint8)


def load_bgr(path: Path) -> np.ndarray:
    """Load an image as a BGR uint8 ndarray (the format OpenCV/InsightFace want)."""

    rgb = load_rgb(path)
    return rgb[:, :, ::-1].copy()


def load_pil(path: Path) -> Image.Image:
    """Load an image as a Pillow RGB image, respecting EXIF orientation."""

    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img.copy()
