"""Microscopy image reading, channel slicing, and browser PNG rendering helpers."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Optional, Sequence

import czifile
import numpy as np
import tifffile
from fastapi import HTTPException
from PIL import Image

IMAGE_PERCENTILE_LOW = 1
IMAGE_PERCENTILE_HIGH = 99
TIFF_SUFFIXES = (".tif", ".tiff")
CZI_SUFFIXES = (".czi",)
SUPPORTED_IMAGE_SUFFIXES = TIFF_SUFFIXES + CZI_SUFFIXES

COLOR_MAP: dict[str, tuple[float, float, float]] = {
    "gray": (1.0, 1.0, 1.0),
    "grey": (1.0, 1.0, 1.0),
    "white": (1.0, 1.0, 1.0),
    "red": (1.0, 0.0, 0.0),
    "green": (0.0, 1.0, 0.0),
    "blue": (0.0, 0.0, 1.0),
    "cyan": (0.0, 1.0, 1.0),
    "magenta": (1.0, 0.0, 1.0),
    "yellow": (1.0, 1.0, 0.0),
}


@dataclass(frozen=True)
class TiffStack:
    """An image array plus axis metadata."""

    array: np.ndarray
    axes: str


def infer_axes(shape: tuple[int, ...], axes: Optional[str]) -> str:
    """Return a best-effort axes string compatible with tifffile conventions."""
    if axes and len(axes) == len(shape):
        return axes
    if len(shape) == 2:
        return "YX"
    if len(shape) == 3:
        if shape[0] <= 32 and shape[1] > 32 and shape[2] > 32:
            return "CYX"
        if shape[2] <= 32 and shape[0] > 32 and shape[1] > 32:
            return "YXC"
        return "CYX"
    if len(shape) == 4:
        if shape[1] <= 32:
            return "TCYX"
        if shape[0] <= 32:
            return "CZYX"
        if shape[-1] <= 32:
            return "ZYXC"
        return "TCYX"
    if len(shape) == 5:
        return "TZCYX"
    return "Q" * len(shape)


def _read_tiff_stack(path: Path) -> TiffStack:
    """Read the first TIFF series and keep enough axis metadata for channel slicing."""
    with tifffile.TiffFile(str(path)) as tif:
        series = tif.series[0]
        array = series.asarray()
        axes = infer_axes(tuple(array.shape), getattr(series, "axes", None))
    return TiffStack(array=np.asarray(array), axes=axes)


def _read_czi_stack(path: Path) -> TiffStack:
    """Read a CZI file into the same array/axes model used by image rendering."""
    with czifile.CziFile(str(path)) as czi:
        array = czi.asarray()
        axes = infer_axes(tuple(array.shape), getattr(czi, "axes", None))
    return TiffStack(array=np.asarray(array), axes=axes)


def read_image_stack(path: Path) -> TiffStack:
    """Read a supported microscopy image and keep axis metadata for channel slicing."""
    suffix = path.suffix.lower()
    if suffix in TIFF_SUFFIXES:
        return _read_tiff_stack(path)
    if suffix in CZI_SUFFIXES:
        return _read_czi_stack(path)
    raise HTTPException(status_code=400, detail=f"Unsupported image file type: {path.suffix}")


def get_channel_axis(stack: TiffStack) -> Optional[int]:
    """Return the channel axis index, or None for a single-channel 2D image."""
    if stack.array.ndim == 2:
        return None
    if "C" in stack.axes:
        return stack.axes.index("C")
    if "S" in stack.axes and stack.array.shape[stack.axes.index("S")] <= 4:
        return stack.axes.index("S")

    non_spatial = [
        idx
        for idx, axis_name in enumerate(stack.axes)
        if axis_name not in {"Y", "X"} and stack.array.shape[idx] <= 32
    ]
    if non_spatial:
        return non_spatial[0]
    if stack.array.ndim == 3 and stack.array.shape[-1] <= 32:
        return stack.array.ndim - 1
    return 0


def get_stack_channel_count(stack: TiffStack) -> int:
    channel_axis = get_channel_axis(stack)
    if channel_axis is None:
        return 1
    return int(stack.array.shape[channel_axis])


def extract_channel(stack: TiffStack, channel: int) -> np.ndarray:
    """Extract a 2D channel plane, selecting the first time/z plane when present."""
    channel_count = get_stack_channel_count(stack)
    if channel < 0 or channel >= channel_count:
        raise HTTPException(status_code=400, detail=f"Channel index out of range: {channel}")

    data = stack.array
    axes = stack.axes
    channel_axis = get_channel_axis(stack)
    if channel_axis is not None:
        data = np.take(data, channel, axis=channel_axis)
        axes = axes[:channel_axis] + axes[channel_axis + 1 :]

    while data.ndim > 2:
        removable_axis = next(
            (idx for idx, axis_name in enumerate(axes) if axis_name not in {"Y", "X"}),
            0,
        )
        data = np.take(data, 0, axis=removable_axis)
        axes = axes[:removable_axis] + axes[removable_axis + 1 :]

    if data.ndim != 2:
        raise HTTPException(status_code=400, detail=f"Unable to render image shape: {stack.array.shape}")
    return np.asarray(data)


def normalize_channel(channel: np.ndarray) -> np.ndarray:
    """Normalize a single channel image to 8-bit using percentile scaling."""
    vmin = np.percentile(channel, IMAGE_PERCENTILE_LOW)
    vmax = np.percentile(channel, IMAGE_PERCENTILE_HIGH)
    if vmax <= vmin:
        vmax = vmin + 1
    normalized = (channel - vmin) / (vmax - vmin)
    return np.clip(normalized * 255, 0, 255).astype(np.uint8)


def linear_channel_to_uint8(channel: np.ndarray) -> np.ndarray:
    """Convert a single channel image to 8-bit without per-image percentile scaling."""
    if channel.dtype == np.uint8:
        return channel
    if channel.dtype == np.bool_:
        return channel.astype(np.uint8) * 255
    if np.issubdtype(channel.dtype, np.integer):
        info = np.iinfo(channel.dtype)
        max_value = float(info.max)
        if max_value <= 0:
            return np.zeros(channel.shape, dtype=np.uint8)
        channel_float = channel.astype(np.float32)
        if np.issubdtype(channel.dtype, np.signedinteger):
            channel_float = np.clip(channel_float, 0.0, None)

        scale_max = max_value
        if max_value == 65535.0:
            observed_max = float(channel_float.max()) if channel_float.size else 0.0
            if observed_max <= 255.0:
                scale_max = 255.0
            elif observed_max <= 4095.0:
                scale_max = 4095.0
            elif observed_max <= 16383.0:
                scale_max = 16383.0

        scaled = np.clip(channel_float, 0.0, scale_max) * (255.0 / scale_max)
        return scaled.astype(np.uint8)
    if np.issubdtype(channel.dtype, np.floating):
        channel_float = np.nan_to_num(channel.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)
        max_value = float(channel_float.max()) if channel_float.size else 0.0
        if max_value <= 1.0:
            scaled = np.clip(channel_float, 0.0, 1.0) * 255.0
        else:
            scaled = np.clip(channel_float, 0.0, 255.0)
        return scaled.astype(np.uint8)
    return np.clip(channel.astype(np.float32), 0.0, 255.0).astype(np.uint8)


def render_channel(stack: TiffStack, channel: int, normalize: bool = True) -> np.ndarray:
    """Render one channel from an image stack as a 2D uint8 array."""
    channel_data = extract_channel(stack, channel)
    if normalize:
        return normalize_channel(channel_data)
    return linear_channel_to_uint8(channel_data)


def resolve_color(color: str) -> tuple[float, float, float]:
    """Resolve a color name or #RRGGBB string into an RGB multiplier."""
    normalized = color.strip().lower()
    if normalized in COLOR_MAP:
        return COLOR_MAP[normalized]
    if normalized.startswith("#") and len(normalized) in {4, 7}:
        if len(normalized) == 4:
            normalized = "#" + "".join(char * 2 for char in normalized[1:])
        try:
            return (
                int(normalized[1:3], 16) / 255.0,
                int(normalized[3:5], 16) / 255.0,
                int(normalized[5:7], 16) / 255.0,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid composite color: {color}") from exc
    raise HTTPException(status_code=400, detail=f"Unknown composite color: {color}")


def render_composite(
    stack: TiffStack,
    channels: Sequence[int],
    colors: Sequence[str],
    normalize: bool = True,
) -> np.ndarray:
    """Render selected channels into an RGB uint8 composite."""
    if not channels:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    if len(channels) != len(colors):
        raise HTTPException(status_code=400, detail="channels and colors must have the same length")

    rendered_channels = [render_channel(stack, channel, normalize=normalize) for channel in channels]
    reference_shape = rendered_channels[0].shape
    if any(channel.shape != reference_shape for channel in rendered_channels):
        raise HTTPException(status_code=400, detail="Composite channels must have matching shapes")

    composite = np.zeros((*reference_shape, 3), dtype=np.float32)
    for channel_image, color in zip(rendered_channels, colors):
        rgb = np.asarray(resolve_color(color), dtype=np.float32)
        composite += channel_image.astype(np.float32)[..., np.newaxis] * rgb
    return np.clip(composite, 0, 255).astype(np.uint8)


def array_to_png_bytes(array: np.ndarray) -> bytes:
    array = np.asarray(array)
    if array.dtype != np.uint8:
        array = np.clip(array.astype(np.float32), 0.0, 255.0).astype(np.uint8)
    if array.ndim not in {2, 3} or (array.ndim == 3 and array.shape[-1] != 3):
        raise HTTPException(status_code=400, detail=f"Unable to encode PNG shape: {array.shape}")

    image = Image.fromarray(array)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


def _split_glob_patterns(pattern: str) -> list[str]:
    patterns = [
        part.strip()
        for semicolon_part in pattern.split(";")
        for part in semicolon_part.split(",")
        if part.strip()
    ]
    return patterns or ["*"]


def list_image_files(directory: Path, pattern: str) -> list[Path]:
    seen: dict[Path, None] = {}
    for glob_pattern in _split_glob_patterns(pattern):
        for path in directory.glob(glob_pattern):
            if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES:
                seen[path] = None
    return sorted(seen)


read_tiff_stack = read_image_stack
list_tiff_files = list_image_files
