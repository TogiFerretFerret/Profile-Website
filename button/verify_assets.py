#!/usr/bin/env python3
"""Validate this package without rebuilding or overwriting its assets."""
from pathlib import Path
from PIL import Image, ImageChops
import draw_button

HERE = Path(__file__).resolve().parent

def same(a, b):
    return a.size == b.size and ImageChops.difference(a.convert('RGB'), b.convert('RGB')).getbbox() is None

def main():
    expected, cursor = draw_button.draw_default()
    grid, grid_cursor, bg = draw_button.load_grid(HERE / 'riverxia.pixels.json')
    assert same(expected, grid), 'Grid differs from the procedural source'
    assert cursor == grid_cursor, 'Cursor coordinates differ'
    with Image.open(HERE / 'riverxia.png') as im:
        assert im.size == (88, 31)
        assert 'transparency' not in im.info
        png = im.convert('RGB')
        assert same(png, expected), 'PNG differs from the source'
        assert len({png.getpixel((x, y)) for y in range(31) for x in range(88)}) == 13
    frames = []
    with Image.open(HERE / 'riverxia.gif') as im:
        assert im.size == (88, 31) and im.n_frames == 2
        assert im.info['loop'] == 0
        for i in range(2):
            im.seek(i)
            assert 'transparency' not in im.info
            assert im.info['duration'] == draw_button.FRAME_DURATION_MS
            frames.append(im.convert('RGB'))
    assert same(frames[0], png), 'PNG and frame one differ'
    expected_off = expected.copy()
    for point in cursor:
        expected_off.putpixel(point, bg)
    assert same(frames[1], expected_off), 'Unexpected second-frame content'
    changed = {(x, y) for y in range(31) for x in range(88)
               if frames[0].getpixel((x, y)) != frames[1].getpixel((x, y))}
    assert changed == set(cursor) and len(changed) == 3
    assert (HERE / 'riverxia.gif').stat().st_size < 20000
    width = sum(len(draw_button.FONT[c][0]) for c in draw_button.LABEL) + len(draw_button.LABEL)-1
    assert width == 55
    assert len(draw_button.FONT['h']) == 10
    assert all(len(glyph) == 9 for char, glyph in draw_button.FONT.items() if char != 'h')
    print('PASS: 88x31, 13 colors, opaque, 2 frames at 1000 ms, 3 cursor pixels.')
    print('PASS: source == JSON == PNG == GIF frame one; 55x10 label; h stem extended by one pixel.')

if __name__ == '__main__':
    main()
