#!/usr/bin/env python3
"""Wythe's tweaks on top of claude-video-effects (MIT, by @vibha.in.progress).

The stock fx.py is never edited. This file adds options and new effects, then
runs exactly like fx.py (with Traditional Chinese text support from fx_zh.py):

  python scripts/fx_wythe.py <effect> in.mp4 out.mp4 --start 0 --end 5 [--text ...] [--opt k=v]

Added options
  profile-wall   card_y=0.62     vertical centre of the front glass card (0-1 of the frame height)
  glass-widgets  pill_y=0.6      vertical centre of the "Edited by Claude" pill
New effects
  tier-glass     tier-list on see-through liquid glass instead of a dark board
  scribble-track hand-drawn ring that follows an object, with an arrow and a label
                 track=track.json (from track_object.py), text=label
"""
import inspect, json, math, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fx_zh  # noqa: E402,F401  (Chinese font support; also imports fx)
import fx  # noqa: E402


def _patch(fn, pairs, new_name=None):
    """Re-create a stock function with small source substitutions, inside fx's namespace."""
    src = inspect.getsource(fn)
    src = '\n'.join(l for l in src.splitlines() if not l.startswith('@effect'))
    for old, new in pairs:
        if old not in src:
            raise RuntimeError(f'fx_wythe: could not find {old!r} in {fn.__name__}')
        src = src.replace(old, new)
    if new_name:
        src = src.replace(f'def {fn.__name__}(', f'def {new_name}(', 1)
    ns = {}
    exec(compile(src, f'<fx_wythe:{fn.__name__}>', 'exec'), fx.__dict__, ns)
    return next(iter(ns.values()))


# profile-wall: movable front card
_pw = _patch(fx.fx_profile_wall, [(
    "cy = min(H * 0.86, c.fy + c.fw * 2.6)",
    "cy = H * float(e.o['card_y']) if 'card_y' in e.o else min(H * 0.86, c.fy + c.fw * 2.6)")])
fx.EFFECTS['profile-wall'] = (_pw, fx.EFFECTS['profile-wall'][1])

# glass-widgets: movable "Edited by Claude" pill
fx.glass_widgets_v2 = _patch(fx.glass_widgets_v2, [(
    "py = H * 0.875", "py = H * float(e.o.get('pill_y', 0.875))")])

# tier-list on liquid glass
_tg = _patch(fx.fx_tier_list, [
    ("im = rrect(cw, chh, W * 0.025, (22, 22, 26, 240))", "im = Image.new('RGBA', (cw, chh), (0, 0, 0, 0))"),
    ("fill=(40, 40, 46, 255))", "fill=(255, 255, 255, 46))"),
    ("fill=(78, 78, 86, 255))", "fill=(0, 0, 0, 120))"),
    # title in front of the speaker, just above the board (close-ups leave no room above the head)
    ("place(c, ttl, W / 2, max(ttl.height * 0.6, c.fy - c.fw * 1.65), 0.9 + 0.1 * ease_out(c.lt / 0.3), 0, al * clamp(c.lt / 0.15), behind=True)", "pass"),
    ("k = ease_back(c.lt / 0.35)",
     "place(c, ttl, W / 2, top - ttl.height * 0.45, 0.9 + 0.1 * ease_out(c.lt / 0.3), 0, al * clamp(c.lt / 0.15), guard=False); k = ease_back(c.lt / 0.35)"),
    ("fill=(225, 225, 230, 255)", "fill=(255, 255, 255, 255)"),
    ("return shadowed(im, 18, 10, 120)", "return im"),
    ("place(c, bd, bx, by, 1, 0, al * clamp(c.lt / 0.12), guard=True)",
     "gp = glass(c, cw, chh, W * 0.025, bx, by, amt=0.12, dark=0.18); "
     "place(c, gp, bx, by, 1, 0, al * clamp(c.lt / 0.12), guard=True); "
     "place(c, bd, bx, by, 1, 0, al * clamp(c.lt / 0.12), guard=True)"),
], new_name='fx_tier_glass')
fx.EFFECTS['tier-glass'] = (_tg, 'the tier list on see-through liquid glass')


# scribble that follows an object
_tracks = {}
def _box_at(path, t):
    if path not in _tracks:
        rows = json.load(open(path))
        sm = []  # light smoothing so the ring does not jitter
        for i in range(len(rows)):
            win = rows[max(0, i - 3): i + 4]
            sm.append([rows[i][0]] + [sum(r[k] for r in win) / len(win) for k in range(1, 5)])
        _tracks[path] = sm
    rows = _tracks[path]
    return min(rows, key=lambda r: abs(r[0] - t))[1:]


@fx.effect('scribble-track', 'a hand-drawn ring follows an object, with an arrow and a label')
def fx_scribble_track(c, e):
    from PIL import Image, ImageDraw
    col = fx.rgb(e.o.get('color'), fx.YELLOW) + (255,); wd = max(6, c.W // 130)
    x0, y0, x1, y1 = _box_at(e.o['track'], e.start + c.lt)
    pad = float(e.o.get('pad', 1.12))
    cx, cy = (x0 + x1) / 2 * c.W, (y0 + y1) / 2 * c.H
    rx, ry = (x1 - x0) / 2 * c.W * pad, (y1 - y0) / 2 * c.H * pad
    lay = Image.new('RGBA', (c.W, c.H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    angs = [-1.9 + 2 * math.pi * 1.08 * i / 69 for i in range(70)]
    ring = [(cx + rx * (1 + 0.04 * math.sin(3 * a)) * math.cos(a), cy + ry * (1 + 0.04 * math.cos(2 * a)) * math.sin(a)) for a in angs]
    fx.hand_path(d, ring, col, wd, fx.ease_inout(c.lt / 0.5))
    # label on the emptier side of the frame, arrow to the ring
    right = cx < c.W / 2
    lx = c.W * (0.74 if right else 0.26); ly = fx.clamp(cy - ry * 0.9, c.H * 0.1, c.H * 0.85)
    tx, ty = cx + (rx * 0.75 if right else -rx * 0.75), cy - ry * 0.55
    pts = fx.arrow_pts(lx, ly + c.W * 0.06, tx, ty, 0.3 if right else -0.3)
    k2 = fx.ease_out((c.lt - 0.45) / 0.35)
    if k2 > 0: fx.hand_path(d, pts, col, wd, k2)
    if k2 >= 0.99: fx.arrow_head(d, pts, col, wd, c.W * 0.035)
    al = fx.clamp((e.d - c.lt) / 0.2)
    fx.comp(c, fx.to_np(lay), 0, 0, al)
    if c.lt > 0.7:
        lab = fx.text_img(e.o.get('text', '看這裡'), c.W * 0.08, 'hand', col[:3], shadow=6)
        fx.place(c, lab, lx, ly, 0.7 + 0.3 * fx.ease_back((c.lt - 0.7) / 0.3), -6 if right else 6, al)


if __name__ == '__main__':
    fx.main()
