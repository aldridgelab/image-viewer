"""Viewer configuration and file-cache state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from image_viewer.backend.channel_utils import normalize_channel_names
from image_viewer.backend.models import DEFAULT_PATTERN
from image_viewer.backend.tiff_io import get_stack_channel_count, read_tiff_stack


class ViewerState:
    """Runtime state for configured TIFF browsing."""

    def __init__(self) -> None:
        self.viewer_dir: Optional[Path] = None
        self.viewer_pattern: str = DEFAULT_PATTERN
        self.viewer_channel_names: list[str] = []
        self.viewer_default_channel: int = 0
        self.viewer_favorites_dir: Optional[Path] = None
        self._file_cache: list[Path] = []
        self._files_by_id: dict[str, Path] = {}
        self._file_info_cache: dict[str, dict[str, object]] = {}

    def clear(self) -> None:
        self.viewer_dir = None
        self.viewer_pattern = DEFAULT_PATTERN
        self.viewer_channel_names = []
        self.viewer_default_channel = 0
        self.viewer_favorites_dir = None
        self._file_cache = []
        self._files_by_id = {}
        self._file_info_cache = {}

    def refresh_file_list(self) -> None:
        self._file_cache = []
        self._files_by_id = {}
        self._file_info_cache = {}
        if not self.viewer_dir or not self.viewer_dir.exists():
            return

        for path in sorted(self.viewer_dir.glob(self.viewer_pattern)):
            if path.suffix.lower() not in (".tif", ".tiff") or not path.is_file():
                continue
            if self.viewer_favorites_dir:
                try:
                    path.relative_to(self.viewer_favorites_dir)
                    continue
                except ValueError:
                    pass
            self._file_cache.append(path)
            self._files_by_id.setdefault(path.stem, path)

    def get_files(self) -> list[Path]:
        return self._file_cache

    def resolve_item_path(self, item_id: str) -> Path:
        if not self.viewer_dir:
            raise HTTPException(status_code=400, detail="Viewer not configured")
        path = self._files_by_id.get(item_id)
        if path and path.exists():
            return path
        self.refresh_file_list()
        path = self._files_by_id.get(item_id)
        if path and path.exists():
            return path
        raise HTTPException(status_code=404, detail=f"Item not found: {item_id}")

    def get_file_info(self, file_path: Path) -> dict[str, object]:
        key = str(file_path)
        if key in self._file_info_cache:
            return self._file_info_cache[key]

        source_path = str(file_path)
        try:
            stat = file_path.stat()
            stack = read_tiff_stack(file_path)
            info: dict[str, object] = {
                "source_path": source_path,
                "shape": list(stack.array.shape),
                "axes": stack.axes,
                "dtype": str(stack.array.dtype),
                "n_channels": get_stack_channel_count(stack),
                "file_size_bytes": stat.st_size,
                "modified_time": stat.st_mtime,
            }
        except Exception:
            info = {
                "source_path": source_path,
                "shape": [],
                "axes": None,
                "dtype": None,
                "n_channels": 0,
                "file_size_bytes": None,
                "modified_time": None,
            }
        self._file_info_cache[key] = info
        return info

    def is_favorite(self, item_id: str) -> bool:
        if not self.viewer_favorites_dir:
            return False
        for ext in (".tif", ".tiff"):
            if (self.viewer_favorites_dir / f"{item_id}{ext}").exists():
                return True
        return False


def load_viewer_config(state: ViewerState, config_path: Path) -> None:
    if not config_path.exists():
        return
    try:
        data = json.loads(config_path.read_text())
    except Exception:
        return

    state.viewer_dir = Path(data["viewer_dir"]) if data.get("viewer_dir") else None
    state.viewer_pattern = str(data.get("viewer_pattern") or DEFAULT_PATTERN)
    raw_names = data.get("viewer_channel_names")
    if isinstance(raw_names, list):
        state.viewer_channel_names = normalize_channel_names(raw_names, max(1, len(raw_names)))
    raw_default_channel = data.get("viewer_default_channel")
    if isinstance(raw_default_channel, int):
        state.viewer_default_channel = max(0, raw_default_channel)
    state.viewer_favorites_dir = (
        Path(data["viewer_favorites_dir"]) if data.get("viewer_favorites_dir") else None
    )

    if state.viewer_dir and not state.viewer_favorites_dir:
        state.viewer_favorites_dir = state.viewer_dir / "favorites"
    if state.viewer_dir and state.viewer_dir.exists():
        state.refresh_file_list()


def save_viewer_config(state: ViewerState, config_path: Path) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "viewer_dir": str(state.viewer_dir) if state.viewer_dir else None,
        "viewer_pattern": state.viewer_pattern,
        "viewer_channel_names": state.viewer_channel_names,
        "viewer_default_channel": state.viewer_default_channel,
        "viewer_favorites_dir": str(state.viewer_favorites_dir) if state.viewer_favorites_dir else None,
    }
    config_path.write_text(json.dumps(payload, indent=2))
