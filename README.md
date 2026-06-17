# Aldridge Lab Image Viewer

Standalone TIFF/CZI image viewer for Aldridge Lab, released as v1.1.0. It scans a directory of `.tif`, `.tiff`, or `.czi` files, renders individual channels, supports favorites, opens clicked images into a full-window channel viewer, and can run either in a browser during development or as a pywebview desktop app.

## What It Does

- Browses multi-channel TIFF and CZI stacks from a local directory.
- Detects channel count and suggests channel names from TIFF/CZI metadata when available.
- Shows a grid thumbnail from the configured default channel, with hold-`Z` hover previews for all channels.
- Opens any image into a full-window viewer with channel controls, zoom/pan, channel thumbnails, metadata, and image-to-image navigation.
- Supports RGB composite rendering, per-channel brightness/contrast, normalization toggles, and PNG exports.

## Quickstart

```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer

# Install Python and frontend dependencies
./scripts/install.sh

# Start backend and frontend
./scripts/start_app.sh
```

Open http://127.0.0.1:5175.

For a one-command install and launch:

```bash
./scripts/quickstart.sh
```

To launch the desktop wrapper locally:

```bash
./scripts/start_desktop.sh
```

To build a macOS `.app` and `.dmg` for distribution:

```bash
./scripts/package_app.sh
```

The package command writes `dist/Aldridge Lab Image Viewer.app` and `dist/AldridgeLabImageViewer-v1.1.0.dmg`.

## Configuration

The browser/dev server workflow stores viewer state in `viewer_config.json` at the repo root. This file is ignored by git. The desktop workflow stores viewer state in `~/Library/Application Support/Image Viewer/viewer_config.json` by default.

Configuration fields:

- `viewer_dir`: local directory containing TIFF/CZI files.
- `viewer_pattern`: semicolon-separated glob pattern for files, default `*.tif;*.tiff;*.czi`.
- `viewer_channel_names`: display labels for detected channels.
- `viewer_default_channel`: zero-based channel index used for grid thumbnails.
- `viewer_favorites_dir`: directory for favorite copies, default `<viewer_dir>/favorites`.

Desktop environment overrides:

- `IMAGE_VIEWER_CONFIG_PATH`: config file path for the backend.
- `IMAGE_VIEWER_FRONTEND_DIST`: production frontend build path.
- `IMAGE_VIEWER_DESKTOP_HOST`: local backend host, default `127.0.0.1`.
- `IMAGE_VIEWER_DESKTOP_PORT`: local backend port, default `0` for an available port.
- `IMAGE_VIEWER_APP_VERSION`: package filename version override, default `1.1.0`.
- `IMAGE_VIEWER_ICON_PATH`: macOS `.icns` file to use for packaging, default `assets/app-icon.icns`.

## Common Workflows

Run backend only:

```bash
uv run uvicorn image_viewer.backend.main:app --host 127.0.0.1 --port 8011 --reload
```

Run frontend only:

```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 5175
```

Verify the repo:

```bash
uv run pytest
cd frontend
npm run lint
npm run build
cd ..
uv run python -m image_viewer.desktop --check
```

Install dependencies only:

```bash
./scripts/install.sh
```

Install dependencies and start both dev servers:

```bash
./scripts/quickstart.sh
```

Launch the desktop app from source:

```bash
./scripts/start_desktop.sh
```

Build the macOS desktop package:

```bash
./scripts/package_app.sh
```

Regenerate the app icon assets:

```bash
uv run python scripts/generate_app_icon.py --output-dir assets
```

## Outputs

- `viewer_config.json`: saved local viewer configuration.
- `~/Library/Application Support/Image Viewer/viewer_config.json`: saved desktop viewer configuration.
- `<viewer_dir>/favorites/`: copied favorite TIFF/CZI files.
- `frontend/dist/`: production frontend build from `npm run build`.
- `assets/app-icon.png` and `assets/app-icon.icns`: generated AL bacteria app icon assets.
- `dist/Aldridge Lab Image Viewer.app`: packaged macOS app bundle.
- `dist/AldridgeLabImageViewer-v1.1.0.dmg`: distributable macOS disk image.
- Browser downloads: current-view PNGs and contact-sheet PNGs.

## Troubleshooting

- Backend connection errors: confirm the backend is running on `127.0.0.1:8011`.
- No files found: check that the directory exists and the pattern matches `.tif`, `.tiff`, or `.czi` files.
- Desktop issues: run `cd frontend && npm run build` if the frontend build is missing; local `.dmg` files are unsigned until an Apple Developer signing/notarization step is added.
