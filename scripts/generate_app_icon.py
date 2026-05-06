"""Generate the Aldridge Lab Image Viewer macOS app icon."""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter

Color = tuple[int, int, int, int]
Point = tuple[float, float]

ICON_SIZE = 1024
ICONSET_SIZES = (16, 32, 64, 128, 256, 512)


def _lerp(start: int, end: int, t: float) -> int:
    return round(start + (end - start) * t)


def _blend(first: Color, second: Color, t: float) -> Color:
    return tuple(_lerp(a, b, t) for a, b in zip(first, second))  # type: ignore[return-value]


def _rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def _draw_background(canvas: Image.Image) -> None:
    top = (8, 11, 15, 255)
    bottom = (18, 24, 30, 255)
    gradient = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)
    for y in range(ICON_SIZE):
        draw.line((0, y, ICON_SIZE, y), fill=_blend(top, bottom, y / (ICON_SIZE - 1)))

    mask = _rounded_mask(ICON_SIZE, 216)
    canvas.paste(gradient, (0, 0), mask)

    glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    glow_draw.ellipse((150, 70, 875, 690), fill=(88, 166, 255, 32))
    glow_draw.ellipse((230, 260, 900, 900), fill=(86, 209, 155, 26))
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(70)))

    border = ImageDraw.Draw(canvas)
    border.rounded_rectangle(
        (18, 18, ICON_SIZE - 19, ICON_SIZE - 19),
        radius=198,
        outline=(79, 100, 119, 120),
        width=8,
    )


def _draw_rod(
    canvas: Image.Image,
    center: Point,
    length: int,
    width: int,
    angle_degrees: float,
    fill: Color,
    accent: Color,
    spots: Sequence[float],
) -> None:
    pad = 34
    layer_size = (length + pad * 2, width + pad * 2)
    layer = Image.new("RGBA", layer_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)

    body = (pad, pad, pad + length, pad + width)
    shadow = (pad + 5, pad + 8, pad + length + 5, pad + width + 8)
    radius = width // 2

    draw.rounded_rectangle(shadow, radius=radius, fill=(0, 0, 0, 72))
    draw.rounded_rectangle(body, radius=radius, fill=fill, outline=(200, 245, 235, 120), width=3)
    draw.rounded_rectangle(
        (pad + 18, pad + 8, pad + length - 18, pad + 17),
        radius=5,
        fill=(255, 255, 255, 56),
    )

    for idx, t in enumerate(spots):
        x = pad + length * t
        y = pad + width * (0.38 + 0.18 * math.sin(idx * 1.7))
        draw.ellipse((x - 7, y - 5, x + 7, y + 5), fill=accent)

    rotated = layer.rotate(angle_degrees, resample=Image.Resampling.BICUBIC, expand=True)
    paste_x = round(center[0] - rotated.width / 2)
    paste_y = round(center[1] - rotated.height / 2)
    canvas.alpha_composite(rotated, (paste_x, paste_y))


def _draw_stroke(
    canvas: Image.Image,
    start: Point,
    end: Point,
    count: int,
    length: int,
    width: int,
    palette: Sequence[tuple[Color, Color]],
) -> None:
    angle = math.degrees(math.atan2(end[1] - start[1], end[0] - start[0]))
    for idx in range(count):
        t = (idx + 0.5) / count
        center = (
            start[0] + (end[0] - start[0]) * t,
            start[1] + (end[1] - start[1]) * t,
        )
        fill, accent = palette[idx % len(palette)]
        spots = (0.25, 0.5, 0.75) if idx % 2 == 0 else (0.34, 0.62)
        _draw_rod(canvas, center, length, width, angle, fill, accent, spots)


def build_icon() -> Image.Image:
    canvas = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    _draw_background(canvas)

    palette = (
        ((88, 166, 255, 245), (214, 235, 255, 116)),
        ((86, 209, 155, 245), (215, 250, 232, 112)),
        ((72, 187, 198, 245), (220, 252, 255, 112)),
    )

    left_start = (286, 780)
    apex = (512, 236)
    right_start = (738, 780)
    cross_left = (392, 565)
    cross_right = (632, 565)

    halo = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    halo_draw.line((left_start, apex), fill=(88, 166, 255, 60), width=86)
    halo_draw.line((right_start, apex), fill=(86, 209, 155, 54), width=86)
    halo_draw.line((cross_left, cross_right), fill=(255, 255, 255, 34), width=72)
    canvas.alpha_composite(halo.filter(ImageFilter.GaussianBlur(22)))

    _draw_stroke(canvas, left_start, apex, count=9, length=128, width=48, palette=palette)
    _draw_stroke(canvas, right_start, apex, count=9, length=128, width=48, palette=palette[1:] + palette[:1])
    _draw_stroke(canvas, cross_left, cross_right, count=4, length=118, width=46, palette=palette[2:] + palette[:2])

    return canvas


def write_iconset(png_path: Path, iconset_dir: Path) -> None:
    iconset_dir.mkdir(parents=True, exist_ok=True)
    source = Image.open(png_path).convert("RGBA")
    for size in ICONSET_SIZES:
        one_x = source.resize((size, size), Image.Resampling.LANCZOS)
        two_x = source.resize((size * 2, size * 2), Image.Resampling.LANCZOS)
        one_x.save(iconset_dir / f"icon_{size}x{size}.png")
        two_x.save(iconset_dir / f"icon_{size}x{size}@2x.png")


def generate_assets(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    png_path = output_dir / "app-icon.png"
    icns_path = output_dir / "app-icon.icns"
    iconset_dir = output_dir / "app-icon.iconset"

    build_icon().save(png_path)
    if iconset_dir.exists():
        shutil.rmtree(iconset_dir)
    write_iconset(png_path, iconset_dir)

    if shutil.which("iconutil"):
        subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
            check=True,
        )
        shutil.rmtree(iconset_dir)
    else:
        print("iconutil not found; PNG generated but .icns was not updated.")

    return png_path, icns_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the app icon assets.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("assets"),
        help="Directory where app-icon.png and app-icon.icns should be written.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    png_path, icns_path = generate_assets(args.output_dir)
    print(f"PNG:  {png_path}")
    if icns_path.exists():
        print(f"ICNS: {icns_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
