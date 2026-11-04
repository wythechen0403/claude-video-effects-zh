#!/usr/bin/env python3
"""Traditional Chinese text support for claude-video-effects.

Use it exactly like fx.py; it only changes how Chinese / Japanese / Korean
characters are drawn:
  python scripts/fx_zh.py liquid-glass-graph in.mp4 out.mp4 --start 2 --end 5 --text "通過率"
  python scripts/fx_zh.py --plan plan.json in.mp4 out.mp4

How it works: the stock fonts have no CJK glyphs, so any text that contains
CJK characters is drawn with Noto Sans TC (fonts/NotoSansTC-VF.ttf, SIL OFL)
at a weight that matches the font the effect asked for. Latin-only text keeps
the effect's original font.
"""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from PIL import ImageDraw, ImageFont  # noqa: E402

ROOT = os.path.dirname(HERE)
ZH_FONT = next((p for p in (
    os.path.join(ROOT, 'fonts', 'NotoSansTC-VF.ttf'),
    '/System/Library/Fonts/PingFang.ttc',            # macOS
    'C:/Windows/Fonts/msjhbd.ttc',                    # Windows, Microsoft JhengHei Bold
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
) if os.path.exists(p)), None)

# weight for each stock font file (heavier display fonts -> heavier Chinese)
_WEIGHT_BY_FILE = {
    'ArchivoBlack': 900, 'Anton': 900, 'PermanentMarker': 700, 'SpaceMono': 700,
    'Montserrat': 800, 'PlayfairDisplay': 700, 'InstrumentSerif': 500, 'Inter': 600,
}


def _is_cjk(text):
    for ch in str(text):
        o = ord(ch)
        if 0x2E80 <= o <= 0x9FFF or 0xAC00 <= o <= 0xD7AF or 0xF900 <= o <= 0xFAFF or 0xFF00 <= o <= 0xFFEF:
            return True
    return False


def _weight_for(f):
    name = os.path.basename(getattr(f, 'path', '') or '')
    for key, w in _WEIGHT_BY_FILE.items():
        if name.startswith(key):
            return w
    return 700


_cache = {}
def _zh(f):
    """Noto Sans TC at the same size as font f, with a matching weight."""
    if ZH_FONT is None or f is None or getattr(f, 'path', None) == ZH_FONT:
        return f
    key = (int(f.size), _weight_for(f))
    if key not in _cache:
        z = ImageFont.truetype(ZH_FONT, key[0])
        try:
            z.set_variation_by_axes([key[1]])
        except Exception:
            pass  # static fallback fonts have no weight axis
        _cache[key] = z
    return _cache[key]


# route CJK text through the Chinese font for drawing and for measuring
_draw_text = ImageDraw.ImageDraw.text
def _text(self, xy, text, fill=None, font=None, *a, **k):
    if font is not None and _is_cjk(text):
        font = _zh(font)
    return _draw_text(self, xy, text, fill, font, *a, **k)
ImageDraw.ImageDraw.text = _text

for _name in ('getbbox', 'getlength', 'getmask', 'getmask2'):
    _orig = getattr(ImageFont.FreeTypeFont, _name)
    def _measure(self, text, *a, _orig=_orig, **k):
        if _is_cjk(text):
            return _orig(_zh(self), text, *a, **k)
        return _orig(self, text, *a, **k)
    setattr(ImageFont.FreeTypeFont, _name, _measure)

import fx  # noqa: E402

if __name__ == '__main__':
    if ZH_FONT is None:
        print('WARNING: no Chinese font found; put NotoSansTC-VF.ttf in fonts/')
    fx.main()
