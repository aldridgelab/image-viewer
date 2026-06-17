from __future__ import annotations

import asyncio

import czifile
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


def test_viewer_backend_inspects_renders_and_favorites_czi(tmp_path, monkeypatch):
    main.CONFIG_PATH = tmp_path / "viewer_config.json"
    main.viewer_state.clear()

    stack = np.stack(
        [
            np.arange(64, dtype=np.uint16).reshape(8, 8),
            np.full((8, 8), 128, dtype=np.uint16),
            np.flipud(np.arange(64, dtype=np.uint16).reshape(8, 8)),
        ]
    )[np.newaxis, ..., np.newaxis]
    metadata = """
    <ImageDocument>
      <Metadata>
        <DisplaySetting>
          <Channels>
            <Channel Id="Channel:0" Name="Colibri DAPI" />
            <Channel Id="Channel:1" Name="Colibri EGFP" />
            <Channel Id="Channel:2" Name="Colibri mCherry" />
          </Channels>
        </DisplaySetting>
      </Metadata>
    </ImageDocument>
    """

    class FakeCziFile:
        axes = "BCYX0"

        def __init__(self, path: str) -> None:
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def asarray(self) -> np.ndarray:
            return stack

        def metadata(self) -> str:
            return metadata

    monkeypatch.setattr(czifile, "CziFile", FakeCziFile)
    (tmp_path / "sample.czi").write_bytes(b"fake czi")

    inspect = run_async(
        main.inspect_viewer_directory(main.ViewerInspectRequest(directory=str(tmp_path)))
    )
    assert inspect.total_images == 1
    assert inspect.sample_id == "sample"
    assert inspect.channel_count == 3
    assert inspect.axes == "BCYX0"
    assert inspect.detected_channel_names == ["Colibri DAPI", "Colibri EGFP", "Colibri mCherry"]

    config = run_async(
        main.set_viewer_config(
            main.ViewerConfigRequest(
                viewer_dir=str(tmp_path),
                viewer_channel_names=inspect.detected_channel_names,
                viewer_default_channel=1,
            )
        )
    )
    assert config.viewer_pattern == "*.tif;*.tiff;*.czi"
    assert config.viewer_default_channel == 1

    items = run_async(main.get_viewer_items())
    assert items.total == 1
    assert items.items[0].id == "sample"
    assert items.items[0].n_channels == 3
    assert items.items[0].dtype == "uint16"
    assert items.items[0].source_path.endswith("sample.czi")

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

    favorite = run_async(
        main.toggle_viewer_favorite("sample", main.ViewerFavoriteRequest(favorite=True))
    )
    assert favorite["is_favorite"] is True
    assert (tmp_path / "favorites" / "sample.czi").exists()

    unfavorite = run_async(
        main.toggle_viewer_favorite("sample", main.ViewerFavoriteRequest(favorite=False))
    )
    assert unfavorite["is_favorite"] is False
    assert not (tmp_path / "favorites" / "sample.czi").exists()


def test_viewer_backend_disambiguates_duplicate_stem_files(tmp_path, monkeypatch):
    main.CONFIG_PATH = tmp_path / "viewer_config.json"
    main.viewer_state.clear()

    czi_stack = np.zeros((1, 1, 8, 8, 1), dtype=np.uint16)

    class FakeCziFile:
        axes = "BCYX0"

        def __init__(self, path: str) -> None:
            self.path = path

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

        def asarray(self) -> np.ndarray:
            return czi_stack

        def metadata(self) -> str:
            return (
                '<ImageDocument><Metadata><DisplaySetting><Channels>'
                '<Channel Id="Channel:0" Name="CZI Channel" />'
                '</Channels></DisplaySetting></Metadata></ImageDocument>'
            )

    monkeypatch.setattr(czifile, "CziFile", FakeCziFile)
    (tmp_path / "sample.czi").write_bytes(b"fake czi")
    tifffile.imwrite(tmp_path / "sample.tif", np.ones((8, 8), dtype=np.uint16))

    run_async(
        main.set_viewer_config(
            main.ViewerConfigRequest(
                viewer_dir=str(tmp_path),
                viewer_channel_names=["Only"],
            )
        )
    )

    items = run_async(main.get_viewer_items())
    assert items.total == 2
    assert sorted(item.id for item in items.items) == ["sample.czi", "sample.tif"]

    czi_response = run_async(main.get_viewer_image("sample.czi", 0, normalize=False))
    assert czi_response.media_type == "image/png"
    tif_response = run_async(main.get_viewer_image("sample.tif", 0, normalize=False))
    assert tif_response.media_type == "image/png"

    run_async(main.toggle_viewer_favorite("sample.czi", main.ViewerFavoriteRequest(favorite=True)))
    favorites = run_async(main.get_viewer_items(favorites_only=True))
    assert [item.id for item in favorites.items] == ["sample.czi"]
    assert (tmp_path / "favorites" / "sample.czi").exists()
