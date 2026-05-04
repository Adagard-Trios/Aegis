"""
Image loading + preprocessing helpers shared by image-modality runtime
adapters (retinal_disease, retinal_age, skin_disease).

Accepts either a filesystem path (str) or an already-decoded PIL image,
returns a normalised numpy array sized to the model's expected input.
PIL is imported lazily so backends without it (lightweight CI containers)
don't pay the cost just to import the adapter modules.
"""
from __future__ import annotations

import logging
import os
from typing import Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

ImageInput = Union[str, "Image.Image", np.ndarray]  # noqa: F821


def _lazy_pil():
    """Import PIL only when actually needed; return (Image, ImageOps) or
    raise ImportError with a helpful hint."""
    try:
        from PIL import Image, ImageOps  # type: ignore
        return Image, ImageOps
    except ImportError as e:
        raise ImportError(
            "Pillow not installed — `pip install Pillow` to enable image-"
            "modality adapters (retinal_disease, retinal_age, skin_disease)."
        ) from e


def load_image(
    src: ImageInput,
    *,
    size: Tuple[int, int] = (224, 224),
    rgb: bool = True,
    normalize: bool = True,
    mean: Optional[Tuple[float, float, float]] = (0.485, 0.456, 0.406),
    std: Optional[Tuple[float, float, float]] = (0.229, 0.224, 0.225),
) -> np.ndarray:
    """Load + preprocess an image to a model-ready numpy array.

    Returns shape (C, H, W) float32 by default — matches the PyTorch
    ImageNet convention used by both RETFound (retinal) and EfficientNet
    (skin / retinal disease classifier).

    Args:
        src: file path, PIL Image, or HxWxC numpy array
        size: target (H, W) — defaults to 224x224 (ViT/EfficientNet input)
        rgb: convert to 3-channel RGB
        normalize: divide by 255 + apply ImageNet mean/std normalisation
        mean, std: per-channel (R, G, B); pass None to skip normalisation
    """
    Image, ImageOps = _lazy_pil()

    if isinstance(src, np.ndarray):
        img = Image.fromarray(src.astype(np.uint8))
    elif isinstance(src, str):
        if not os.path.exists(src):
            raise FileNotFoundError(f"Image not found: {src}")
        img = Image.open(src)
    else:
        img = src   # assume PIL

    if rgb and img.mode != "RGB":
        img = img.convert("RGB")
    img = ImageOps.fit(img, size, method=Image.Resampling.BILINEAR)

    arr = np.asarray(img, dtype=np.float32)  # (H, W, C)
    if normalize:
        arr /= 255.0
        if mean is not None and std is not None:
            arr = (arr - np.array(mean, dtype=np.float32)) / np.array(std, dtype=np.float32)

    # Channels-first for PyTorch / torchvision conventions
    arr = np.transpose(arr, (2, 0, 1))   # (C, H, W)
    return arr


def safe_load_image(src: ImageInput, **kwargs) -> Optional[np.ndarray]:
    """Same as load_image but never raises — returns None on any failure
    (missing file, missing PIL, decode error). Adapters use this when
    they want to fall through to LLM-only mode rather than blow up."""
    try:
        return load_image(src, **kwargs)
    except Exception as e:
        logger.warning(f"image load failed: {e}")
        return None
