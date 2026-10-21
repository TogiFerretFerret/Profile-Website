#!/usr/bin/env python3
"""Draw riverxia.sh directly on an 88x31 integer pixel grid.

Requirements: Python 3.9+ and Pillow.

    python3 draw_button.py --out-dir rebuilt
    python3 draw_button.py --pixels riverxia.pixels.json --out-dir edited

No fonts, original reference image, resampling, dithering, or external assets
are used. The default drawing uses hand-placed bitmap lettering with a one-pixel-taller h stem.
The optional JSON input provides an editable, complete pixel grid.
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from PIL import Image, ImageChops
except ImportError as exc:
    raise SystemExit("Install the dependency first: python3 -m pip install Pillow") from exc

RGB = Tuple[int, int, int]
WIDTH, HEIGHT = 88, 31
PALETTE: Dict[str, RGB] = {
    "bg": (0, 0, 20),
    "blue": (102, 204, 255),
    "pink": (255, 0, 255),
    "yellow": (255, 255, 0),
    "green": (0, 255, 0),
    "white": (255, 255, 255),
    "hair_light": (186, 146, 255),
    "hair_mid": (144, 98, 235),
    "hair_dark": (92, 56, 184),
    "blush": (255, 140, 230),
    "skin": (252, 236, 246),
    "eye": (96, 0, 112),
    "detail": (28, 16, 64),
}

# Native-size bitmap glyphs, not scaled lettering. Most glyphs are nine
# rows high. The h has one extra top stem pixel (ten rows), aligned to the
# same baseline; its shoulder, width, and all existing pixels stay in place.
# Most letters are five pixels wide; r, i and the period are narrower.
FONT: Dict[str, List[str]] = {
    "r": ["0000", "0000", "1110", "1001", "1000", "1000", "1000", "1000", "1000"],
    "i": ["010", "000", "110", "010", "010", "010", "010", "010", "111"],
    "v": ["00000", "00000", "10001", "10001", "10001", "10001", "10001", "01010", "00100"],
    "e": ["00000", "00000", "01110", "10001", "10001", "11111", "10000", "10000", "01111"],
    "x": ["00000", "00000", "10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "a": ["00000", "00000", "01110", "00001", "00001", "01111", "10001", "10001", "01111"],
    ".": ["0", "0", "0", "0", "0", "0", "0", "0", "1"],
    "s": ["00000", "00000", "01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "h": ["10000", "10000", "10000", "11110", "10001", "10001", "10001", "10001", "10001", "10001"],
}
LABEL = "riverxia.sh"
TEXT_ORIGIN = (24, 10)
TEXT_GAP = 1
GLYPH_BASE_HEIGHT = 9
FRAME_DURATION_MS = 1000


def draw_default() -> Tuple[Image.Image, List[Tuple[int, int]]]:
    """Draw the static, cursor-on design; also return its cursor positions."""
    image = Image.new("RGB", (WIDTH, HEIGHT), PALETTE["bg"])
    pixels = image.load()

    def pixel(x: int, y: int, color: str) -> None:
        # Fail loudly on a layout error instead of silently clipping text.
        if not 0 <= x < WIDTH or not 0 <= y < HEIGHT:
            raise ValueError("Drawing out of bounds at ({}, {})".format(x, y))
        pixels[x, y] = PALETTE[color]

    # Two nested one-pixel outlines.
    for x in range(WIDTH):
        pixel(x, 0, "blue")
        pixel(x, HEIGHT - 1, "blue")
    for y in range(HEIGHT):
        pixel(0, y, "blue")
        pixel(WIDTH - 1, y, "blue")
    for x in range(1, WIDTH - 1):
        pixel(x, 1, "pink")
        pixel(x, HEIGHT - 2, "pink")
    for y in range(1, HEIGHT - 1):
        pixel(1, y, "pink")
        pixel(WIDTH - 2, y, "pink")

    # Mascot coordinates are relative to this origin.
    ox, oy = 4, 8

    def dots(points: List[Tuple[int, int]], color: str) -> None:
        for x, y in points:
            pixel(ox + x, oy + y, color)

    dots([
        (2, 0), (3, 1), (4, 2), (5, 3), (6, 3), (7, 2), (8, 1),
        (9, 1), (10, 2), (11, 3), (12, 3), (13, 2), (14, 1), (15, 0),
        (1, 1), (1, 2), (1, 3), (2, 4), (3, 5), (4, 6), (5, 6),
        (6, 6), (7, 6), (8, 6), (9, 6), (10, 6), (11, 6), (12, 6),
        (13, 5), (14, 4), (15, 3), (15, 2), (15, 1),
        (2, 7), (3, 7), (4, 7), (5, 7), (6, 7), (7, 7), (8, 7),
        (9, 7), (10, 7), (11, 7), (12, 7), (13, 7),
        (2, 8), (13, 8), (2, 9), (13, 9), (2, 10), (13, 10),
        (2, 11), (13, 11), (3, 12), (4, 12), (5, 12), (6, 12),
        (7, 12), (8, 12), (9, 12), (10, 12), (11, 12), (12, 12),
        (4, 13), (5, 13), (10, 13), (11, 13),
    ], "hair_dark")
    for y in range(2, 12):
        for x in range(3, 13):
            if abs(x - 8) + abs(y - 7) < 10:
                pixel(ox + x, oy + y, "hair_mid")
    dots([
        (2, 1), (3, 2), (4, 3), (5, 4), (12, 4), (13, 3),
        (14, 2), (15, 1), (11, 3), (10, 2),
    ], "hair_mid")
    dots([
        (4, 4), (5, 4), (6, 3), (7, 3), (8, 3), (9, 3), (10, 4),
        (11, 4), (5, 5), (8, 4), (10, 5), (6, 5), (7, 5), (9, 5),
    ], "hair_light")
    for y in range(8, 13):
        for x in range(4, 12):
            pixel(ox + x, oy + y, "skin")
    dots([(3, 2), (4, 3), (4, 4), (13, 2), (12, 3), (12, 4)], "blush")
    dots([(5, 7), (7, 7), (9, 7), (11, 7)], "hair_dark")
    dots([(5, 9), (6, 9), (9, 9), (10, 9), (5, 10), (10, 10)], "eye")
    dots([(6, 9), (10, 9)], "white")
    dots([(4, 11), (11, 11)], "blush")
    dots([(7, 11), (8, 12), (9, 11)], "eye")
    dots([
        (2, 13), (3, 13), (4, 13), (2, 14), (3, 14), (4, 14),
        (11, 13), (12, 13), (13, 13), (11, 14), (12, 14), (13, 14),
    ], "skin")
    dots([(3, 14), (12, 14)], "detail")
    dots([(14, 9), (15, 10), (15, 11), (15, 12), (14, 13), (13, 13)], "hair_mid")
    dots([(14, 10), (14, 11), (14, 12)], "hair_dark")

    # Keep three small stars above the taller wordmark.
    for x, y, color in [
        (28, 6, "yellow"), (45, 5, "pink"), (78, 6, "blue"),
    ]:
        for dx, dy in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
            pixel(x + dx, y + dy, color)

    # Build a literal foreground pixel mask before drawing either shadow.
    # This also makes the text's exact extent independently testable.
    mask = []
    x, y = TEXT_ORIGIN
    for character in LABEL:
        glyph = FONT[character]
        glyph_width = len(glyph[0])
        if len(glyph) not in (9, 10) or any(len(row) != glyph_width for row in glyph):
            raise ValueError("Malformed glyph: {!r}".format(character))
        for yy, row in enumerate(glyph):
            for xx, value in enumerate(row):
                if value not in "01":
                    raise ValueError("Glyphs must contain only 0 and 1.")
                if value == "1":
                    # Extra rows extend upward rather than moving the baseline.
                    mask.append((x + xx, y + yy + GLYPH_BASE_HEIGHT - len(glyph)))
        x += glyph_width + TEXT_GAP
    right_exclusive = x - TEXT_GAP

    # Cyan at (+2,+2), pink at (+1,+1), then the yellow foreground.
    # Content must stay INSIDE the border, not just inside the image bounds.
    for dx, dy, color in [(2, 2, "blue"), (1, 1, "pink"), (0, 0, "yellow")]:
        for xx, yy in mask:
            if not (2 <= xx + dx <= WIDTH - 3 and 2 <= yy + dy <= HEIGHT - 3):
                raise ValueError("Text/shadow would touch or cross the border.")
            pixel(xx + dx, yy + dy, color)

    # The text is 55 px wide; its furthest shadow ends at x=80.
    # Three cursor pixels at x=82..84 leave a gap before the border at x=86.
    cursor = [(xx, y + 8) for xx in range(right_exclusive + 3, right_exclusive + 6)]
    for xx, yy in cursor:
        if not (2 <= xx <= WIDTH - 3 and 2 <= yy <= HEIGHT - 3):
            raise ValueError("The cursor would touch or cross the border.")
        if pixels[xx, yy] != PALETTE["bg"]:
            raise ValueError("The blinking cursor overlaps other artwork.")
        pixel(xx, yy, "green")
    return image, cursor


def load_grid(path: Path) -> Tuple[Image.Image, List[Tuple[int, int]], RGB]:
    """Load a literal pixel map; one character corresponds to one pixel."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if (data["width"], data["height"]) != (WIDTH, HEIGHT):
        raise ValueError("The editable grid must be exactly 88x31.")
    palette = {}
    for key, value in data["palette"].items():
        if len(key) != 1 or len(value) != 7 or not value.startswith("#"):
            raise ValueError("Use one-character palette keys and #RRGGBB colors.")
        palette[key] = tuple(int(value[i:i + 2], 16) for i in (1, 3, 5))
    rows = data["rows"]
    if len(rows) != HEIGHT or any(len(row) != WIDTH for row in rows):
        raise ValueError("Expected 31 rows of exactly 88 characters each.")
    image = Image.new("RGB", (WIDTH, HEIGHT))
    image.putdata([palette[key] for row in rows for key in row])
    cursor = [tuple(point) for point in data["cursor"]["pixels"]]
    for point in cursor:
        if len(point) != 2 or not 0 <= point[0] < WIDTH or not 0 <= point[1] < HEIGHT:
            raise ValueError("Invalid cursor coordinate: {!r}".format(point))
    background = palette[data["cursor"]["off_color"]]
    return image, cursor, background


def indexed(image: Image.Image, colors: List[RGB]) -> Image.Image:
    """Assign palette indices exactly, without quantization or dithering."""
    result = Image.new("P", image.size)
    lookup = {color: index for index, color in enumerate(colors)}
    result.putdata([lookup[image.getpixel((x, y))]
                    for y in range(HEIGHT) for x in range(WIDTH)])
    flat = [component for color in colors for component in color]
    result.putpalette(flat + [0] * (768 - len(flat)))
    return result


def save_assets(image: Image.Image, cursor: List[Tuple[int, int]],
                background: RGB, directory: Path) -> None:
    """Write and then verify the static PNG, two-frame GIF and editable grid."""
    if image.size != (WIDTH, HEIGHT):
        raise ValueError("Unexpected image dimensions.")
    second = image.copy()
    for point in cursor:
        second.putpixel(point, background)
    colors = sorted({frame.getpixel((x, y))
                     for frame in (image, second)
                     for y in range(HEIGHT) for x in range(WIDTH)})
    if len(colors) > 16:
        raise ValueError("The button must use at most 16 colors.")
    frames = [indexed(frame, colors) for frame in (image, second)]
    directory.mkdir(parents=True, exist_ok=True)
    png_path, gif_path = directory / "riverxia.png", directory / "riverxia.gif"
    frames[0].save(png_path, bits=4, optimize=True)
    frames[0].save(
        gif_path, save_all=True, append_images=frames[1:],
        duration=[FRAME_DURATION_MS, FRAME_DURATION_MS], loop=0, disposal=1, optimize=False,
    )
    symbols = "0123456789ABCDEF"
    lookup = {color: symbols[index] for index, color in enumerate(colors)}
    grid = {
        "width": WIDTH, "height": HEIGHT,
        "palette": {
            symbols[i]: "#{:02x}{:02x}{:02x}".format(*color)
            for i, color in enumerate(colors)
        },
        "rows": [
            "".join(lookup[image.getpixel((x, y))] for x in range(WIDTH))
            for y in range(HEIGHT)
        ],
        "cursor": {
            "pixels": cursor, "off_color": lookup[background],
            "frame_durations_ms": [FRAME_DURATION_MS, FRAME_DURATION_MS],
        },
    }
    (directory / "riverxia.pixels.json").write_text(
        json.dumps(grid, indent=2) + "\n", encoding="utf-8"
    )
    with Image.open(png_path) as saved:
        assert saved.size == (WIDTH, HEIGHT) and "transparency" not in saved.info
        assert ImageChops.difference(saved.convert("RGB"), image).getbbox() is None
    with Image.open(gif_path) as saved:
        assert saved.size == (WIDTH, HEIGHT) and saved.n_frames == 2
        for index, expected in enumerate((image, second)):
            saved.seek(index)
            assert "transparency" not in saved.info
            assert saved.info.get("duration") == FRAME_DURATION_MS
            assert ImageChops.difference(saved.convert("RGB"), expected).getbbox() is None
    if gif_path.stat().st_size >= 20_000:
        raise ValueError("The GIF exceeds the requested size budget.")
    print("Wrote 88x31 PNG and GIF; {} colors; GIF {} bytes.".format(
        len(colors), gif_path.stat().st_size))
    print("Verified PNG == GIF frame 1; opaque frames; no resampling.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("dist"))
    parser.add_argument("--pixels", type=Path, help="Draw an edited pixel-grid JSON instead.")
    args = parser.parse_args()
    if args.pixels:
        image, cursor, background = load_grid(args.pixels)
    else:
        image, cursor = draw_default()
        background = PALETTE["bg"]
    save_assets(image, cursor, background, args.out_dir)


if __name__ == "__main__":
    main()
