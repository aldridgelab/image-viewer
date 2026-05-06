"""Pydantic API models for the TIFF image viewer."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel

DEFAULT_PATTERN = "*.tif"


class ViewerInspectRequest(BaseModel):
    """Request body for inspecting a viewer directory."""

    directory: str
    pattern: str = DEFAULT_PATTERN


class ViewerInspectResponse(BaseModel):
    """Response for viewer inspect endpoint."""

    total_images: int
    sample_id: Optional[str] = None
    image_shape: Optional[list[int]] = None
    axes: Optional[str] = None
    channel_count: int
    default_channel_names: list[str]
    detected_channel_names: list[str] = []
    channel_name_source: Literal["metadata", "default"] = "default"


class ViewerConfigRequest(BaseModel):
    """Request body for setting viewer configuration."""

    viewer_dir: str
    viewer_pattern: str = DEFAULT_PATTERN
    viewer_channel_names: list[str]
    viewer_default_channel: int = 0
    viewer_favorites_dir: Optional[str] = None


class ViewerConfigResponse(BaseModel):
    """Response for viewer configuration endpoints."""

    viewer_dir: Optional[str] = None
    viewer_pattern: str = DEFAULT_PATTERN
    viewer_channel_names: list[str] = []
    viewer_default_channel: int = 0
    viewer_favorites_dir: Optional[str] = None


class ViewerItem(BaseModel):
    """Single item in viewer listing."""

    id: str
    filename: str
    source_path: str
    is_favorite: bool = False
    n_channels: int
    shape: list[int]
    dtype: Optional[str] = None
    axes: Optional[str] = None
    file_size_bytes: Optional[int] = None
    modified_time: Optional[float] = None


class ViewerItemsResponse(BaseModel):
    """Response for viewer items endpoint."""

    items: list[ViewerItem]
    total: int


class ViewerFavoriteRequest(BaseModel):
    """Request body for favoriting or unfavoriting a viewer item."""

    favorite: bool


class ViewerContactSheetExportRequest(BaseModel):
    """Request body for exporting a contact sheet PNG."""

    search: Optional[str] = None
    limit: int = 50
    favorites_only: bool = False
    render_mode: Literal["single", "composite"] = "single"
    single_channel: int = 0
    composite_channels: Optional[dict[str, Optional[int]]] = None
    normalize: bool = True
