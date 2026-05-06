# Usage Guide

## Pipeline Overview

Inputs -> Inspect TIFF directory -> Configure channels -> Browse grid/composites -> Inspect full-window view -> Export PNGs/contact sheets -> Optional desktop package

## Directory Setup

Use the setup panel to enter a local directory and file pattern. The default pattern is `*.tif`; `.tiff` files are supported when the pattern matches them, such as `*.tiff` or `*.tif*`.

The backend reads the first matching TIFF to determine shape, axes, and channel count. It also checks OME-XML, ImageJ labels, and JSON image descriptions for channel names.

## Install Scripts

From the repo root:

```bash
./scripts/install.sh
```

This runs `uv sync` for the backend and `npm install` in `frontend/`.

```bash
./scripts/quickstart.sh
```

This runs the same install step, then starts the backend and frontend through `scripts/start_app.sh`.

```bash
./scripts/start_desktop.sh
```

This launches the viewer in a pywebview desktop window. If `frontend/dist/index.html` is missing, it builds the frontend first. The desktop app keeps its config at `~/Library/Application Support/Image Viewer/viewer_config.json` by default.

```bash
./scripts/package_app.sh
```

This builds the production frontend, bundles the app with PyInstaller, and writes `dist/Aldridge Lab Image Viewer.app` plus `dist/AldridgeLabImageViewer-v1.0.0.dmg`. The generated app is unsigned; clean external distribution still needs Apple Developer signing and notarization.

## Browsing

Grid cards render the configured default channel with linear 8-bit conversion so fluorescence intensity comparisons are not normalized per image. The toolbar can switch the grid to RGB composite mode and map detected channels into red, green, and blue. Holding `Z` while hovering over a grid card shows every channel for that TIFF.

Clicking a grid card opens the full-window viewer. The app header remains visible, and the selected image area provides channel controls, a channel thumbnail rail, favorite toggling, metadata, and previous/next image movement within the current filtered list.

Full-window controls include zoom in/out, reset-to-fit, mouse-wheel zooming, drag-to-pan while zoomed, per-channel brightness and contrast sliders, and a normalize toggle. Keyboard shortcut hints are exposed through button tooltips.

The export button in the full-window toolbar downloads the current rendered image. The contact-sheet export button in the grid toolbar downloads a PNG sheet for the current search/favorite filter using either the single-channel or RGB composite mode.

Holding `Z` while hovering over a grid card shows a compact all-channel preview. Long file names are truncated in the popup header so they stay within the preview.

## Desktop App

The desktop launcher starts the FastAPI backend on `127.0.0.1` with an available port, serves the built React app from the same process, and opens that local app inside a native pywebview window titled `Aldridge Lab - v1.0.0`.

Useful environment variables:

- `IMAGE_VIEWER_CONFIG_PATH`: config file path for the backend.
- `IMAGE_VIEWER_FRONTEND_DIST`: production frontend build path.
- `IMAGE_VIEWER_DESKTOP_HOST`: local backend host, default `127.0.0.1`.
- `IMAGE_VIEWER_DESKTOP_PORT`: local backend port, default `0` for an available port.
- `IMAGE_VIEWER_LOG_LEVEL`: Uvicorn log level for the desktop backend.
- `IMAGE_VIEWER_APP_VERSION`: package filename version override, default `1.0.0`.

## API Summary

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Backend health check |
| `POST` | `/api/viewer/inspect` | Inspect a directory and sample TIFF |
| `GET` | `/api/viewer/config` | Read saved viewer config |
| `POST` | `/api/viewer/config` | Save viewer config and refresh files |
| `GET` | `/api/viewer/items` | List TIFF items with search/favorite filters |
| `GET` | `/api/viewer/image/{item_id}/{channel}` | Render a channel as PNG |
| `GET` | `/api/viewer/composite/{item_id}` | Render RGB/composite channels as PNG |
| `POST` | `/api/viewer/export/contact-sheet` | Export the current filtered list as a contact-sheet PNG |
| `POST` | `/api/viewer/item/{item_id}/favorite` | Copy/remove favorite TIFF |
| `POST` | `/api/viewer/refresh` | Refresh cached file list |
| `POST` | `/api/viewer/clear` | Clear saved viewer config |

## Verification

```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer
uv run pytest
cd frontend
npm run lint
npm run build
cd ..
uv run python -m image_viewer.desktop --check
bash -n scripts/start_desktop.sh scripts/package_app.sh
```
