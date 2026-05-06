"""FastAPI backend for the standalone TIFF image viewer."""

from __future__ import annotations

import os
import random as random_module
import shutil
import sys
from io import BytesIO
from math import ceil, sqrt
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont

from image_viewer import __version__
from image_viewer.backend.channel_utils import (
    default_channel_names,
    normalize_channel_names,
    suggest_channel_names_from_tiff,
)
from image_viewer.backend.models import (
    DEFAULT_PATTERN,
    ViewerConfigRequest,
    ViewerConfigResponse,
    ViewerContactSheetExportRequest,
    ViewerFavoriteRequest,
    ViewerInspectRequest,
    ViewerInspectResponse,
    ViewerItem,
    ViewerItemsResponse,
)
from image_viewer.backend.state import (
    ViewerState,
    load_viewer_config,
    save_viewer_config,
)
from image_viewer.backend.tiff_io import (
    array_to_png_bytes,
    get_stack_channel_count,
    list_tiff_files,
    read_tiff_stack,
    render_channel,
    render_composite,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(
    os.environ.get("IMAGE_VIEWER_CONFIG_PATH", str(PROJECT_ROOT / "viewer_config.json"))
).expanduser()
FRONTEND_DIST_ENV = "IMAGE_VIEWER_FRONTEND_DIST"
DEFAULT_COMPOSITE_COLORS: tuple[str, ...] = (
    "gray",
    "green",
    "magenta",
    "cyan",
    "yellow",
    "red",
    "blue",
)
CONTACT_SHEET_THUMBNAIL_SIZE = 160
CONTACT_SHEET_LABEL_HEIGHT = 36
CONTACT_SHEET_GAP = 12
CONTACT_SHEET_MARGIN = 12
CONTACT_SHEET_MAX_LIMIT = 200

viewer_state = ViewerState()
load_viewer_config(viewer_state, CONFIG_PATH)
_frontend_dist_dir: Optional[Path] = None
_frontend_fallback_registered = False

app = FastAPI(
    title="Image Viewer API",
    description="Standalone TIFF channel viewer API.",
    version=__version__,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def resolve_frontend_dist(frontend_dist: Optional[Path] = None) -> Path:
    """Find the production frontend build for desktop/static serving."""
    candidates: list[Path] = []
    if frontend_dist:
        candidates.append(frontend_dist)
    if os.environ.get(FRONTEND_DIST_ENV):
        candidates.append(Path(os.environ[FRONTEND_DIST_ENV]))
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.append(Path(sys._MEIPASS) / "frontend" / "dist")  # type: ignore[attr-defined]
    candidates.append(PROJECT_ROOT / "frontend" / "dist")

    searched: list[str] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        searched.append(str(resolved))
        if (resolved / "index.html").exists():
            return resolved

    raise RuntimeError(
        "Frontend build not found. Run `npm run build` in frontend/ or set "
        f"{FRONTEND_DIST_ENV}. Searched: {', '.join(searched)}"
    )


def mount_frontend_dist(frontend_dist: Optional[Path] = None) -> Path:
    """Serve the built React app from the same FastAPI process."""
    global _frontend_dist_dir, _frontend_fallback_registered

    _frontend_dist_dir = resolve_frontend_dist(frontend_dist)
    assets_dir = _frontend_dist_dir / "assets"
    has_assets_mount = any(getattr(route, "name", None) == "frontend-assets" for route in app.routes)
    if assets_dir.exists() and not has_assets_mount:
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    if not _frontend_fallback_registered:

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str) -> FileResponse:
            if full_path.startswith("api/"):
                raise HTTPException(status_code=404, detail="Not found")
            if _frontend_dist_dir is None:
                raise HTTPException(status_code=404, detail="Frontend not mounted")

            if full_path:
                requested = (_frontend_dist_dir / full_path).resolve()
                try:
                    requested.relative_to(_frontend_dist_dir)
                except ValueError as exc:
                    raise HTTPException(status_code=404, detail="Not found") from exc
                if requested.is_file():
                    return FileResponse(requested)

            return FileResponse(_frontend_dist_dir / "index.html")

        _frontend_fallback_registered = True

    return _frontend_dist_dir


def _parse_csv_ints(value: str) -> list[int]:
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise HTTPException(status_code=400, detail="At least one channel is required")
    try:
        return [int(part) for part in parts]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid channel list: {value}") from exc


def _parse_csv_colors(value: Optional[str], count: int) -> list[str]:
    colors = [part.strip() for part in value.split(",") if part.strip()] if value else []
    if not colors:
        return [DEFAULT_COMPOSITE_COLORS[idx % len(DEFAULT_COMPOSITE_COLORS)] for idx in range(count)]
    if len(colors) != count:
        raise HTTPException(status_code=400, detail="channels and colors must have the same length")
    return colors


def _matching_viewer_files(search: Optional[str], favorites_only: bool) -> list[Path]:
    if not viewer_state.viewer_dir:
        return []

    files = viewer_state.get_files()
    if favorites_only:
        files = [path for path in files if viewer_state.is_favorite(path.stem)]
    if search:
        search_lower = search.lower()
        files = [path for path in files if search_lower in path.name.lower()]
    return files


def _viewer_item_from_path(file_path: Path) -> ViewerItem:
    info = viewer_state.get_file_info(file_path)
    dtype = info.get("dtype")
    file_size_bytes = info.get("file_size_bytes")
    modified_time = info.get("modified_time")
    return ViewerItem(
        id=file_path.stem,
        filename=file_path.name,
        source_path=str(info.get("source_path") or file_path),
        is_favorite=viewer_state.is_favorite(file_path.stem),
        n_channels=int(info.get("n_channels", 0)),
        shape=list(info.get("shape", [])),
        dtype=str(dtype) if dtype else None,
        axes=str(info.get("axes")) if info.get("axes") else None,
        file_size_bytes=int(file_size_bytes) if file_size_bytes is not None else None,
        modified_time=float(modified_time) if modified_time is not None else None,
    )


def _render_item_array(
    file_path: Path,
    channel: int,
    composite_channels: Optional[list[int]],
    composite_colors: Optional[list[str]],
    normalize: bool,
) -> object:
    stack = read_tiff_stack(file_path)
    if composite_channels is not None and composite_colors is not None:
        return render_composite(
            stack,
            channels=composite_channels,
            colors=composite_colors,
            normalize=normalize,
        )
    return render_channel(stack, channel, normalize=normalize)


def _array_to_contact_thumbnail(array: object, size: int) -> Image.Image:
    image = Image.fromarray(array).convert("RGB")
    image.thumbnail((size, size), Image.Resampling.BILINEAR)
    thumbnail = Image.new("RGB", (size, size), (16, 18, 20))
    thumbnail.paste(image, ((size - image.width) // 2, (size - image.height) // 2))
    return thumbnail


def _truncate_label(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    font: ImageFont.ImageFont,
) -> str:
    if draw.textlength(text, font=font) <= max_width:
        return text
    suffix = "..."
    truncated = text
    while truncated and draw.textlength(truncated + suffix, font=font) > max_width:
        truncated = truncated[:-1]
    return truncated + suffix if truncated else suffix


def _contact_sheet_png_bytes(
    files: list[Path],
    channel: int,
    composite_channels: Optional[list[int]],
    composite_colors: Optional[list[str]],
    normalize: bool,
) -> bytes:
    font = ImageFont.load_default()
    if not files:
        sheet = Image.new("RGB", (420, 120), (248, 248, 248))
        draw = ImageDraw.Draw(sheet)
        draw.text((18, 48), "No matching images", fill=(32, 36, 40), font=font)
        buffer = BytesIO()
        sheet.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.getvalue()

    count = len(files)
    columns = max(1, min(5, ceil(sqrt(count))))
    rows = ceil(count / columns)
    cell_width = CONTACT_SHEET_THUMBNAIL_SIZE
    cell_height = CONTACT_SHEET_THUMBNAIL_SIZE + CONTACT_SHEET_LABEL_HEIGHT
    sheet_width = (
        CONTACT_SHEET_MARGIN * 2
        + columns * cell_width
        + (columns - 1) * CONTACT_SHEET_GAP
    )
    sheet_height = (
        CONTACT_SHEET_MARGIN * 2
        + rows * cell_height
        + (rows - 1) * CONTACT_SHEET_GAP
    )
    sheet = Image.new("RGB", (sheet_width, sheet_height), (244, 246, 248))
    draw = ImageDraw.Draw(sheet)

    for idx, file_path in enumerate(files):
        row = idx // columns
        column = idx % columns
        x = CONTACT_SHEET_MARGIN + column * (cell_width + CONTACT_SHEET_GAP)
        y = CONTACT_SHEET_MARGIN + row * (cell_height + CONTACT_SHEET_GAP)
        rendered = _render_item_array(
            file_path,
            channel=channel,
            composite_channels=composite_channels,
            composite_colors=composite_colors,
            normalize=normalize,
        )
        thumbnail = _array_to_contact_thumbnail(rendered, CONTACT_SHEET_THUMBNAIL_SIZE)
        sheet.paste(thumbnail, (x, y))
        draw.rectangle(
            (x, y, x + CONTACT_SHEET_THUMBNAIL_SIZE - 1, y + CONTACT_SHEET_THUMBNAIL_SIZE - 1),
            outline=(196, 202, 208),
        )
        label = _truncate_label(draw, file_path.name, cell_width, font)
        draw.text(
            (x, y + CONTACT_SHEET_THUMBNAIL_SIZE + 7),
            label,
            fill=(24, 30, 36),
            font=font,
        )

    buffer = BytesIO()
    sheet.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer.getvalue()


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/viewer/inspect")
async def inspect_viewer_directory(request: ViewerInspectRequest) -> ViewerInspectResponse:
    directory = Path(request.directory).expanduser().resolve()
    if not directory.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.directory}")
    if not directory.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.directory}")

    files = list_tiff_files(directory, request.pattern)
    if not files:
        return ViewerInspectResponse(
            total_images=0,
            image_shape=None,
            axes=None,
            channel_count=0,
            default_channel_names=[],
            detected_channel_names=[],
        )

    sample_path = files[0]
    try:
        stack = read_tiff_stack(sample_path)
        channel_count = get_stack_channel_count(stack)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read sample image: {exc}") from exc

    detected_names, source = suggest_channel_names_from_tiff(sample_path, channel_count)
    return ViewerInspectResponse(
        total_images=len(files),
        sample_id=sample_path.stem,
        image_shape=list(stack.array.shape),
        axes=stack.axes,
        channel_count=channel_count,
        default_channel_names=default_channel_names(channel_count),
        detected_channel_names=detected_names,
        channel_name_source=source,
    )


@app.get("/api/viewer/config")
async def get_viewer_config() -> ViewerConfigResponse:
    return ViewerConfigResponse(
        viewer_dir=str(viewer_state.viewer_dir) if viewer_state.viewer_dir else None,
        viewer_pattern=viewer_state.viewer_pattern,
        viewer_channel_names=viewer_state.viewer_channel_names,
        viewer_default_channel=viewer_state.viewer_default_channel,
        viewer_favorites_dir=(
            str(viewer_state.viewer_favorites_dir) if viewer_state.viewer_favorites_dir else None
        ),
    )


@app.post("/api/viewer/config")
async def set_viewer_config(request: ViewerConfigRequest) -> ViewerConfigResponse:
    viewer_dir = Path(request.viewer_dir).expanduser().resolve()
    if not viewer_dir.exists():
        raise HTTPException(status_code=404, detail=f"Directory not found: {request.viewer_dir}")
    if not viewer_dir.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.viewer_dir}")

    viewer_state.viewer_dir = viewer_dir
    viewer_state.viewer_pattern = request.viewer_pattern or DEFAULT_PATTERN
    viewer_state.viewer_favorites_dir = (
        Path(request.viewer_favorites_dir).expanduser().resolve()
        if request.viewer_favorites_dir
        else viewer_dir / "favorites"
    )
    viewer_state.viewer_favorites_dir.mkdir(parents=True, exist_ok=True)
    viewer_state.refresh_file_list()

    files = viewer_state.get_files()
    sample_channel_count = 1
    if files:
        sample_info = viewer_state.get_file_info(files[0])
        sample_channel_count = max(1, int(sample_info.get("n_channels", 1)))
    viewer_state.viewer_channel_names = normalize_channel_names(
        request.viewer_channel_names,
        sample_channel_count,
    )
    viewer_state.viewer_default_channel = min(
        max(0, request.viewer_default_channel),
        max(0, len(viewer_state.viewer_channel_names) - 1),
    )
    save_viewer_config(viewer_state, CONFIG_PATH)

    return await get_viewer_config()


@app.get("/api/viewer/items")
async def get_viewer_items(
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    random: bool = False,
    seed: Optional[int] = None,
    favorites_only: bool = False,
) -> ViewerItemsResponse:
    if not viewer_state.viewer_dir:
        return ViewerItemsResponse(items=[], total=0)

    files = viewer_state.get_files()
    if favorites_only:
        files = [path for path in files if viewer_state.is_favorite(path.stem)]
    if search:
        search_lower = search.lower()
        files = [path for path in files if search_lower in path.name.lower()]

    total = len(files)
    limit = min(max(limit, 1), 1000)
    offset = max(offset, 0)
    if random:
        rng = random_module.Random(seed)
        files = rng.sample(files, min(limit, total)) if limit < total else files[:]
        rng.shuffle(files)
    else:
        files = files[offset : offset + limit]

    items = [_viewer_item_from_path(file_path) for file_path in files]
    return ViewerItemsResponse(items=items, total=total)


@app.get("/api/viewer/image/{item_id}/{channel}")
async def get_viewer_image(item_id: str, channel: int, normalize: bool = True) -> StreamingResponse:
    input_path = viewer_state.resolve_item_path(item_id)
    try:
        stack = read_tiff_stack(input_path)
        rendered = render_channel(stack, channel, normalize=normalize)
        png_bytes = array_to_png_bytes(rendered)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load image: {exc}") from exc

    return StreamingResponse(
        BytesIO(png_bytes),
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600"},
    )


@app.get("/api/viewer/composite/{item_id}")
async def get_viewer_composite(
    item_id: str,
    channels: Optional[str] = None,
    colors: Optional[str] = None,
    red_channel: Optional[int] = None,
    green_channel: Optional[int] = None,
    blue_channel: Optional[int] = None,
    normalize: bool = True,
) -> StreamingResponse:
    input_path = viewer_state.resolve_item_path(item_id)
    if channels:
        channel_indices = _parse_csv_ints(channels)
        color_names = _parse_csv_colors(colors, len(channel_indices))
    else:
        channel_indices = []
        color_names = []
        for channel, color in (
            (red_channel, "red"),
            (green_channel, "green"),
            (blue_channel, "blue"),
        ):
            if channel is not None:
                channel_indices.append(channel)
                color_names.append(color)
        if not channel_indices:
            raise HTTPException(status_code=400, detail="At least one composite channel is required")
    try:
        stack = read_tiff_stack(input_path)
        rendered = render_composite(
            stack,
            channels=channel_indices,
            colors=color_names,
            normalize=normalize,
        )
        png_bytes = array_to_png_bytes(rendered)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to load composite: {exc}") from exc

    return StreamingResponse(
        BytesIO(png_bytes),
        media_type="image/png",
        headers={"Cache-Control": "max-age=3600"},
    )


@app.get("/api/viewer/contact-sheet")
async def get_viewer_contact_sheet(
    search: Optional[str] = None,
    favorites_only: bool = False,
    limit: int = 50,
    channel: int = 0,
    channels: Optional[str] = None,
    colors: Optional[str] = None,
    normalize: bool = True,
) -> StreamingResponse:
    if not viewer_state.viewer_dir:
        raise HTTPException(status_code=400, detail="Viewer not configured")

    limit = min(max(limit, 1), CONTACT_SHEET_MAX_LIMIT)
    files = _matching_viewer_files(search, favorites_only)[:limit]
    composite_channels = _parse_csv_ints(channels) if channels else None
    composite_colors = (
        _parse_csv_colors(colors, len(composite_channels)) if composite_channels is not None else None
    )
    if colors and composite_channels is None:
        raise HTTPException(status_code=400, detail="colors requires channels")

    try:
        png_bytes = _contact_sheet_png_bytes(
            files,
            channel=channel,
            composite_channels=composite_channels,
            composite_colors=composite_colors,
            normalize=normalize,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build contact sheet: {exc}") from exc

    return StreamingResponse(
        BytesIO(png_bytes),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/viewer/export/contact-sheet")
async def post_viewer_contact_sheet(
    request: ViewerContactSheetExportRequest,
) -> StreamingResponse:
    if not viewer_state.viewer_dir:
        raise HTTPException(status_code=400, detail="Viewer not configured")

    limit = min(max(request.limit, 1), CONTACT_SHEET_MAX_LIMIT)
    files = _matching_viewer_files(request.search, request.favorites_only)[:limit]
    composite_channels: Optional[list[int]] = None
    composite_colors: Optional[list[str]] = None
    if request.render_mode == "composite":
        composite_channels = []
        composite_colors = []
        for color in ("red", "green", "blue"):
            channel = (request.composite_channels or {}).get(color)
            if channel is not None:
                composite_channels.append(channel)
                composite_colors.append(color)
        if not composite_channels:
            raise HTTPException(status_code=400, detail="Composite export requires at least one channel")

    try:
        png_bytes = _contact_sheet_png_bytes(
            files,
            channel=request.single_channel,
            composite_channels=composite_channels,
            composite_colors=composite_colors,
            normalize=request.normalize,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to build contact sheet: {exc}") from exc

    return StreamingResponse(
        BytesIO(png_bytes),
        media_type="image/png",
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/viewer/item/{item_id}/favorite")
async def toggle_viewer_favorite(
    item_id: str,
    request: ViewerFavoriteRequest,
) -> dict[str, object]:
    if not viewer_state.viewer_favorites_dir:
        raise HTTPException(status_code=400, detail="Favorites directory not configured")

    source_path = viewer_state.resolve_item_path(item_id)
    favorite_path = viewer_state.viewer_favorites_dir / source_path.name
    if request.favorite:
        viewer_state.viewer_favorites_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, favorite_path)
    elif favorite_path.exists():
        favorite_path.unlink()
    return {"status": "ok", "id": item_id, "is_favorite": request.favorite}


@app.post("/api/viewer/refresh")
async def refresh_viewer_files() -> dict[str, int | str]:
    if not viewer_state.viewer_dir:
        raise HTTPException(status_code=400, detail="Viewer not configured")
    viewer_state.refresh_file_list()
    return {"status": "ok", "total": len(viewer_state.get_files())}


@app.post("/api/viewer/clear")
async def clear_viewer_config() -> ViewerConfigResponse:
    viewer_state.clear()
    save_viewer_config(viewer_state, CONFIG_PATH)
    return ViewerConfigResponse()
