"""Channel naming and resolution helpers for microscopy viewer APIs."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence

import czifile
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


def _local_xml_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _extract_czi_channel_names(metadata_xml: str) -> list[str]:
    try:
        root = ET.fromstring(metadata_xml)
    except ET.ParseError:
        return []

    indexed_names: dict[int, str] = {}
    fallback_names: list[str] = []
    for element in root.iter():
        if _local_xml_name(element.tag) != "Channel":
            continue
        name = element.attrib.get("Name", "").strip()
        if not name:
            continue

        channel_id = element.attrib.get("Id", "")
        if channel_id.startswith("Channel:"):
            try:
                channel_index = int(channel_id.split(":", 1)[1])
            except ValueError:
                channel_index = -1
            if channel_index >= 0:
                indexed_names.setdefault(channel_index, name)
                continue

        if name not in fallback_names:
            fallback_names.append(name)

    if indexed_names:
        return [name for _, name in sorted(indexed_names.items())]
    return fallback_names


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


def _suggest_channel_names_from_tiff(path: Path) -> list[str]:
    with tifffile.TiffFile(str(path)) as tif:
        if tif.ome_metadata:
            ome_names = _extract_ome_channel_names(tif.ome_metadata)
            if ome_names:
                return ome_names

        imagej_names = _extract_imagej_labels(tif.imagej_metadata)
        if imagej_names:
            return imagej_names

        description = tif.pages[0].description if tif.pages else None
        return _extract_json_description_names(description)


def _suggest_channel_names_from_czi(path: Path) -> list[str]:
    with czifile.CziFile(str(path)) as czi:
        metadata = czi.metadata()
    if isinstance(metadata, str):
        return _extract_czi_channel_names(metadata)
    return []


def suggest_channel_names_from_image(path: Path, channel_count: int) -> tuple[list[str], str]:
    """Suggest channel names from image metadata, falling back to defaults."""
    defaults = default_channel_names(channel_count)
    try:
        if path.suffix.lower() == ".czi":
            metadata_names = _suggest_channel_names_from_czi(path)
        else:
            metadata_names = _suggest_channel_names_from_tiff(path)
        if metadata_names:
            return normalize_channel_names(metadata_names, channel_count), "metadata"
    except Exception:
        pass

    return defaults, "default"


suggest_channel_names_from_tiff = suggest_channel_names_from_image
