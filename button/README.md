# riverxia.sh — one-pixel h-stem adjustment

The h stem is one pixel taller than the previous 55x9 lettering.
The label now spans 55x10 pixels; its baseline, shoulder, width and spacing
are unchanged. Only three image pixels changed: the new yellow stem pixel
at (74, 9), its pink shadow at (75, 10), and blue shadow at (76, 11).
Coordinates are zero-based. All other pixels are unchanged in both frames.
The full `riverxia.sh` label fits, including both offset shadows and the cursor.
The mascot and the two one-pixel border outlines are preserved. Three stars
sit above the lettering.

## Files

- `riverxia.png`: static 88x31 PNG, indexed, opaque, 13 used colors.
- `riverxia.gif`: 88x31 GIF, two one-second frames, looping; 2,130 bytes.
  Frame one matches the PNG. Only three green cursor pixels blink.
- `draw_button.py`: complete Python source: glyph bitmaps, mascot coordinates,
  colors, borders, animation, export and pixel-verification logic.
- `riverxia.pixels.json`: complete editable 88x31 pixel grid and palette.
- `verify_assets.py`: checks dimensions, exact source/grid reproduction,
  palette size, frame timing, opacity, and the changed cursor pixels.
- `preview_8x.png`: nearest-neighbor inspection image, not the website asset.
- `preview.html`: native-size preview plus an explicitly labeled 8x inspection
  view. Both inspection previews are display-only, not 2x artwork variants.
- `requirements.txt`: Pillow dependency.
- `SHA256SUMS.txt`: checksums of the other package files.

No font file or reference image is needed to rebuild. Glyphs are literal
rows of binary pixels in the source. The drawing routine makes an 88x31
canvas directly and does not resize, quantize, dither or antialias it.

## Rebuild

Requires Python 3.9+ and Pillow. Extract the ZIP, then:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python draw_button.py --out-dir rebuilt
.venv/bin/python verify_assets.py
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.
The verification script checks the files in its own folder.

## Edit the design

Edit `FONT`, `PALETTE`, `TEXT_ORIGIN`, or `draw_default()` in the Python source.
Letters use up to five columns and nine rows, except the ten-row `h`.
Glyphs align to the same baseline; narrow `r`, `i` and `.` glyphs
leave room for the complete domain. There is a one-pixel gap between glyphs.
The last foreground text pixel is at x=78, the cyan shadow ends at x=80,
and the cursor uses x=82..84. The right inner border is at x=86.

Text and cursor writes are checked against the inner border. A layout that
would clip raises an error instead of silently dropping pixels.

For single-pixel changes, edit `riverxia.pixels.json`: each character is exactly
one pixel, with 31 rows of 88 characters. Then:

```sh
.venv/bin/python draw_button.py --pixels riverxia.pixels.json --out-dir edited
```

The JSON records which pixels turn off in the second frame. Animation timing
is controlled by `FRAME_DURATION_MS` in the script; the JSON duration field
records that timing and is not independently applied on import.

## Website markup

```html
<picture>
  <source media="(prefers-reduced-motion: reduce)" srcset="riverxia.png">
  <img src="riverxia.gif" width="88" height="31" alt="riverxia.sh">
</picture>
```

Use 88x31 CSS pixels for the intended size. `image-rendering: pixelated` may be
used for enlarged display-only previews. The downloadable assets remain 88x31.

No credit required. Optional credit: "Pixel button made with ChatGPT."
