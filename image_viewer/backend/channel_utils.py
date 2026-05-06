"""Channel naming and resolution helpers for TIFF viewer APIs."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

import tifffile

DEFAULT_CHANNEL_NAMES: tuple[str, ...] = ("Phase", "HADA", "Bodipy")


def default_channel_names(channel_count: int) -> list[str]:
    """Return default channel names for a given channel count."""
    names: list[str] = []
    for idx in range(max(0, channel_count)):
        if idx < len(DEFAULT_CHANNEL_NAMES):
            names.append(DEFAULT_CHANNEL_NAMES[idx])
        else:
            names.append(f"Channel {idx + 1}")
    return names


def normalize_channel_names(names: Sequence[str] | None, channel_count: int) -> list[str]:
    """Normalize channel names to a fixed length with sensible defaults."""
    defaults = default_channel_names(channel_count)
    if not names:
        return defaults

    normalized = defaults[:]
    for idx in range(min(len(names), channel_count)):
        candidate = str(names[idx]).strip()
        if candidate:
            normalized[idx] = candidate
    return normalized


def _extract_ome_channel_names(ome_xml: str) -> list[str]:
    try:
        root = ET.fromstring(ome_xml)
    except ET.ParseError:
        return []

    namespace: dict[str, str] = {}
    if root.tag.startswith("{"):
        namespace["ome"] = root.tag.split("}", 1)[0][1:]
        query = ".//ome:Channel"
    else:
        query = ".//Channel"

    names: list[str] = []
    for channel in root.findall(query, namespace):
        name = channel.attrib.get("Name", "").strip()
        if name:
            names.append(name)
    return names


def _extract_imagej_labels(imagej_metadata: dict | None) -> list[str]:
    if not imagej_metadata:
        return []

    labels = imagej_metadata.get("Labels")
    if not isinstance(labels, list):
        return []

    output: list[str] = []
    for label in labels:
        clean = str(label).strip()
        if clean:
            output.append(clean)
    return output


def _extract_json_description_names(description: str | None) -> list[str]:
    if not description:
        return []
    try:
        payload = json.loads(description)
    except json.JSONDecodeError:
        return []

    for key in ("channel_names", "channels"):
        value = payload.get(key)
        if isinstance(value, list) and value:
            output = [str(item).strip() for item in value if str(item).strip()]
            if output:
                return output
    return []


def suggest_channel_names_from_tiff(path: Path, channel_count: int) -> tuple[list[str], str]:
    """Suggest channel names from TIFF metadata, falling back to defaults."""
    defaults = default_channel_names(channel_count)
    try:
        with tifffile.TiffFile(str(path)) as tif:
            if tif.ome_metadata:
                ome_names = _extract_ome_channel_names(tif.ome_metadata)
                if ome_names:
                    return normalize_channel_names(ome_names, channel_count), "metadata"

            imagej_names = _extract_imagej_labels(tif.imagej_metadata)
            if imagej_names:
                return normalize_channel_names(imagej_names, channel_count), "metadata"

            description = tif.pages[0].description if tif.pages else None
            description_names = _extract_json_description_names(description)
            if description_names:
                return normalize_channel_names(description_names, channel_count), "metadata"
    except Exception:
        pass

    return defaults, "default"
