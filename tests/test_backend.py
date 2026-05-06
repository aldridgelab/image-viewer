from __future__ import annotations

import asyncio

import numpy as np
import tifffile

from image_viewer.backend import main


def run_async(coro):
    return asyncio.run(coro)


def test_viewer_backend_inspects_renders_and_favorites_tif(tmp_path):
    main.CONFIG_PATH = tmp_path / "viewer_config.json"
    main.viewer_state.clear()

    stack = np.stack(
        [
            np.arange(64, dtype=np.uint16).reshape(8, 8),
            np.full((8, 8), 128, dtype=np.uint16),
            np.flipud(np.arange(64, dtype=np.uint16).reshape(8, 8)),
        ]
    )
    tifffile.imwrite(tmp_path / "sample.tif", stack)

    inspect = run_async(
        main.inspect_viewer_directory(
            main.ViewerInspectRequest(directory=str(tmp_path), pattern="*.tif")
        )
    )
    assert inspect.total_images == 1
    assert inspect.sample_id == "sample"
    assert inspect.channel_count == 3

    config = run_async(
        main.set_viewer_config(
            main.ViewerConfigRequest(
                viewer_dir=str(tmp_path),
                viewer_pattern="*.tif",
                viewer_channel_names=["Phase", "HADA", "Bodipy"],
                viewer_default_channel=1,
            )
        )
    )
    assert config.viewer_default_channel == 1

    items = run_async(main.get_viewer_items())
    assert items.total == 1
    assert items.items[0].id == "sample"
    assert items.items[0].n_channels == 3
    assert items.items[0].dtype == "uint16"
    assert items.items[0].source_path.endswith("sample.tif")

    response = run_async(main.get_viewer_image("sample", 1, normalize=False))
    assert response.media_type == "image/png"

    composite = run_async(
        main.get_viewer_composite(
            "sample",
            red_channel=0,
            green_channel=1,
            blue_channel=2,
            normalize=False,
        )
    )
    assert composite.media_type == "image/png"

    contact_sheet = run_async(
        main.post_viewer_contact_sheet(
            main.ViewerContactSheetExportRequest(
                render_mode="composite",
                composite_channels={"red": 0, "green": 1, "blue": 2},
                limit=10,
                normalize=False,
            )
        )
    )
    assert contact_sheet.media_type == "image/png"

    favorite = run_async(
        main.toggle_viewer_favorite("sample", main.ViewerFavoriteRequest(favorite=True))
    )
    assert favorite["is_favorite"] is True
    assert (tmp_path / "favorites" / "sample.tif").exists()

    unfavorite = run_async(
        main.toggle_viewer_favorite("sample", main.ViewerFavoriteRequest(favorite=False))
    )
    assert unfavorite["is_favorite"] is False
    assert not (tmp_path / "favorites" / "sample.tif").exists()
