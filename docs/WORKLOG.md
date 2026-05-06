# Worklog

## 2026-05-06 - Bacteria A App Icon

**What changed**
- Added a generated `A` app icon built from rod-shaped bacteria.
- Added `assets/app-icon.png` for preview and `assets/app-icon.icns` for macOS packaging.
- Added `scripts/generate_app_icon.py` so the icon can be regenerated from source geometry.
- Updated `scripts/package_app.sh` to regenerate and use the default `.icns` icon, with `IMAGE_VIEWER_ICON_PATH` available for overrides.

**Why**
- Give the desktop app a lab-specific icon instead of the default PyInstaller icon.

**How to verify**
```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer
uv run python scripts/generate_app_icon.py --output-dir assets
bash -n scripts/start_desktop.sh scripts/package_app.sh
uv run pytest
cd frontend
npm run lint
npm run build
cd ..
./scripts/package_app.sh
"dist/Aldridge Lab Image Viewer.app/Contents/MacOS/Aldridge Lab Image Viewer" --check
```

**Follow-ups / TODOs**
- Add Apple Developer codesigning and notarization if the `.dmg` will be distributed outside trusted/internal machines.

## 2026-05-06 - v1.0.0 Release Branding

**What changed**
- Added an `AL` monogram mark to the app header.
- Updated the visible app title to `Aldridge Lab - v1.0.0`, with the version rendered in light grey.
- Bumped Python, backend API, frontend package, and lockfile metadata to `1.0.0`.
- Updated the desktop window title to `Aldridge Lab - v1.0.0`.
- Updated desktop packaging defaults to write `dist/Aldridge Lab Image Viewer.app` and `dist/AldridgeLabImageViewer-v1.0.0.dmg`.

**Why**
- Cut a clear v1.0.0 release with consistent branding and versioned distributable filenames.

**How to verify**
```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer
uv run pytest
cd frontend
npm run lint
npm run build
cd ..
uv run python -m image_viewer.desktop --check
bash -n scripts/start_desktop.sh scripts/package_app.sh
./scripts/package_app.sh
"dist/Aldridge Lab Image Viewer.app/Contents/MacOS/Aldridge Lab Image Viewer" --check
```

**Follow-ups / TODOs**
- Add Apple Developer codesigning and notarization if the `.dmg` will be distributed outside trusted/internal machines.

## 2026-05-06 - Desktop Packaging and Hover Filename Fix

**What changed**
- Truncated long TIFF names in the hold-`Z` channel preview popup so they no longer overflow across the image preview.
- Added a pywebview desktop launcher that serves the built React frontend from FastAPI and opens it in a native macOS window.
- Added `scripts/start_desktop.sh` for launching the desktop app from source.
- Added `scripts/package_app.sh` for building `dist/Image Viewer.app` and `dist/ImageViewer.dmg`.
- Added desktop config path handling under `~/Library/Application Support/Image Viewer/viewer_config.json`.

**Why**
- Make the hover preview visually stable for long microscopy filenames.
- Let the viewer be distributed as a double-clickable desktop app instead of only as a browser workflow.

**How to verify**
```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer
uv run pytest
cd frontend
npm run lint
npm run build
cd ..
uv run python -m image_viewer.desktop --check
bash -n scripts/start_desktop.sh scripts/package_app.sh
./scripts/package_app.sh
"dist/Image Viewer.app/Contents/MacOS/Image Viewer" --check
```

**Follow-ups / TODOs**
- Add Apple Developer codesigning and notarization if the `.dmg` will be distributed outside trusted/internal machines.

## 2026-05-06 - Full Viewer Controls and Exports

**What changed**
- Added full-window zoom, pan, reset-to-fit, brightness, contrast, and normalization controls.
- Added RGB composite rendering with red/green/blue channel mapping in the grid and backend composite PNG rendering.
- Added metadata display for selected TIFFs, including source path, shape, axes, dtype, size, modified time, and channel names.
- Added current-view PNG export and filtered contact-sheet PNG export.
- Added backend item metadata and contact-sheet/composite API coverage in tests.

**Why**
- Make the standalone viewer more useful for inspecting multi-channel TIFFs and exporting review artifacts.

**How to verify**
```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer
uv run pytest
cd frontend
npm run lint
npm run build
```

**Follow-ups / TODOs**
- None.

## 2026-05-06 - Quick Install Scripts

**What changed**
- Added `scripts/install.sh` to install backend dependencies with `uv sync` and frontend dependencies with `npm install`.
- Added `scripts/quickstart.sh` to run installation and then launch the app through `scripts/start_app.sh`.
- Updated README and usage docs with the new install commands.

**Why**
- Make first-time setup and local launch a one-command workflow.

**How to verify**
```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer
./scripts/install.sh
cd frontend
npm run build
```

**Follow-ups / TODOs**
- None.

## 2026-05-06 - Standalone TIFF Image Viewer

**What changed**
- Created a new `image-viewer` repo with a FastAPI backend and React/Vite frontend.
- Extracted the TIFF directory inspection, channel rendering, file listing, favorites, and channel naming behavior from the existing segmentation app.
- Added a clicked full-window image view with channel flipping, channel thumbnails, favorite toggling, and previous/next image navigation.
- Kept hold-`Z` grid hover previews for all channels.

**Why**
- The original image viewer was embedded in a larger segmentation review app. This isolates TIFF browsing into a focused app for channel inspection and comparison.

**How to verify**
```bash
cd /Users/jwhite22/Documents/aldridge-multiomics/image-viewer
uv run pytest
cd frontend
npm run build
```

**Follow-ups / TODOs**
- Add drag-and-drop directory selection if the app later runs with a desktop shell that can safely expose local file paths.
