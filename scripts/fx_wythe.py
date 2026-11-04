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


# glass text: a giant see-through glass word behind the speaker
@fx.effect('glass-text', 'a giant see-through glass word rises in behind you, with a light sweep')
def fx_glass_text(c, e):
    import numpy as np, cv2
    from PIL import Image, ImageDraw
    W, H = c.W, c.H
    txt = e.o.get('text', 'CLAUDE')

    def build():
        kind = e.o.get('font', 'anton'); size = int(W * 0.42)
        while size > 20 and fx.font(kind, size).getlength(txt) > W * float(e.o.get('width', 0.94)): size = int(size * 0.94)
        f = fx.font(kind, size); bb = f.getbbox(txt); pad = int(size * 0.25)
        im = Image.new('L', (bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad), 0)
        ImageDraw.Draw(im).text((pad - bb[0], pad - bb[1]), txt, font=f, fill=255)
        m = np.asarray(im, np.float32) / 255
        sm = cv2.GaussianBlur(m, (0, 0), max(2, size * 0.035))
        gx = cv2.Sobel(sm, cv2.CV_32F, 1, 0, ksize=5); gy = cv2.Sobel(sm, cv2.CV_32F, 0, 1, ksize=5)
        n = np.sqrt(gx ** 2 + gy ** 2).max() or 1
        return m, gx / n, gy / n
    m, gx, gy = fx.cached(e, 'glass', build)
    h, w = m.shape
    k = fx.ease_out(c.lt / 0.6); out = fx.clamp((e.d - c.lt) / 0.3)
    cy = H * float(e.o['y']) if 'y' in e.o else fx.clamp(c.fy - c.fw * 0.3, H * 0.14, H * 0.5)
    x0 = int(W / 2 - w / 2); y0 = int(cy - h / 2 + (1 - k) * H * 0.06)
    # crop the frame behind the word (clipped to the frame)
    xs = np.clip(np.arange(x0, x0 + w), 0, W - 1); ys = np.clip(np.arange(y0, y0 + h), 0, H - 1)
    bg = np.ascontiguousarray(c.img[np.ix_(ys, xs)])
    blur = cv2.GaussianBlur(bg, (0, 0), max(3, W / 140))
    # refraction: bend the room through the letter edges
    amt = W * float(e.o.get('refract', 0.06))
    mx, my = np.meshgrid(np.arange(w, dtype=np.float32), np.arange(h, dtype=np.float32))
    refr = cv2.remap(blur, mx + gx * amt, my + gy * amt, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
    tint = float(e.o.get('tint', 0.06))
    glass = refr * (1 - tint) + tint
    # light from the top-left on the rims, a darker rim on the opposite side
    lit = np.clip(-(gx + gy) * 1.6, 0, 1)[..., None]; dark = np.clip((gx + gy) * 1.2, 0, 1)[..., None]
    glass = glass + lit * 0.55 - dark * 0.22
    # a slow light sweep across the word
    sx = (c.lt / max(0.8, e.d)) * (w * 1.6) - w * 0.3
    band = np.clip(1 - np.abs(mx + (my - h / 2) * 0.5 - sx) / (w * 0.06), 0, 1)[..., None]
    glass = np.clip(glass + band * 0.22, 0, 1)
    alpha = (m * k * out)[..., None]
    # soft shadow on the wall, then the glass
    sh = cv2.GaussianBlur(np.roll(m, int(h * 0.04), axis=0), (0, 0), max(4, w * 0.01))[..., None] * 0.28 * k * out
    fx.comp(c, np.dstack([np.zeros_like(bg), sh]), x0, y0, 1, behind=True)
    fx.comp(c, np.dstack([glass, alpha]), x0, y0, 1, behind=True)


# glow chart: a glowing line draws itself across the frame while a big number counts up
@fx.effect('glow-chart', 'a glowing line chart draws itself across you while a big number counts up')
def fx_glow_chart(c, e):
    import re
    import numpy as np, cv2
    from PIL import Image, ImageDraw
    W, H = c.W, c.H
    col = fx.rgb(e.o.get('color'), (255, 214, 64))
    vals = [float(v) for v in str(e.o.get('values', '8|12|10|18|16|28|40|62|100')).split('|')]
    lo, hi = min(vals), max(vals); span = (hi - lo) or 1
    yb = fx.clamp(c.fy + c.fw * 3.2, H * 0.3, H * 0.8); yt = fx.clamp(c.fy - c.fw * 0.6, H * 0.08, yb - H * 0.1)
    x0, x1 = W * 0.04, W * 0.9
    pts = [(x0 + (x1 - x0) * i / (len(vals) - 1), yb - (yb - yt) * (v - lo) / span) for i, v in enumerate(vals)]
    p = fx.ease_inout(c.lt / float(e.o.get('draw', 1.4)))
    out = fx.clamp((e.d - c.lt) / 0.3)
    # dim the room a little (not the person) so the glow reads on light walls
    dim = float(e.o.get('dim', 0.28)) * fx.clamp(c.lt / 0.4) * out
    if dim > 0: c.img = c.img * (1 - dim * (1 - c.m[..., None]))
    # the part of the line drawn so far
    seg = len(pts) - 1; f = p * seg; n = int(f)
    path = pts[:n + 1]
    if n < seg:
        a, b = pts[n], pts[n + 1]; t = f - n; path = path + [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)]
    lay = np.zeros((H, W), np.float32)
    if len(path) > 1:
        im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
        d.line(path, fill=255, width=max(5, W // 110), joint='curve')
        core = np.asarray(im, np.float32) / 255
        glow = cv2.GaussianBlur(core, (0, 0), W / 90) * 2.6 + cv2.GaussianBlur(core, (0, 0), W / 30) * 1.8
        lay = np.clip(np.maximum(core, glow), 0, 1)
        # glowing tip
        ex, ey = path[-1]; tip = np.zeros((H, W), np.float32); cv2.circle(tip, (int(ex), int(ey)), max(6, W // 70), 1.0, -1)
        lay = np.clip(lay + cv2.GaussianBlur(tip, (0, 0), W / 60) * 2.5 + tip, 0, 1)
    rgb = np.empty((H, W, 3), np.float32); rgb[:] = np.float32(col) / 255
    whiteish = np.clip(rgb + (lay[..., None] > 0.85) * 0.6, 0, 1)
    fx.comp(c, np.dstack([whiteish, lay * out]), 0, 0, 1, guard=True)
    # the number counts up once the line is halfway
    to = str(e.o.get('to', '+320%')); m = re.search(r'[\d.]+', to)
    if m and c.lt > 0.3:
        num = float(m.group()); k = fx.ease_out((c.lt - 0.3) / 1.2)
        shown = to[:m.start()] + (f'{num * k:.0f}' if '.' not in m.group() else f'{num * k:.1f}') + to[m.end():]
        big = fx.text_img(shown, W * 0.12, 'uib', (255, 250, 225), glow=(col, W * 0.012))
        fx.place(c, big, W * 0.9 - big.width / 2 + W * 0.04, yt - W * 0.05, 0.8 + 0.2 * fx.ease_back((c.lt - 0.3) / 0.4), 0, out * fx.clamp((c.lt - 0.3) / 0.2), guard=True)
        if e.o.get('text'):
            lab = fx.text_img(e.o['text'], W * 0.045, 'uib', (255, 250, 225), shadow=4)
            fx.place(c, lab, W * 0.9 - lab.width / 2 + W * 0.04, yt - W * 0.05 + big.height * 0.42, 1, 0, out * fx.clamp((c.lt - 0.5) / 0.2), guard=True)


# chat drop: a chat window slides down behind the speaker's head, a request pops in and the reply types itself
def _wrap(f, s, maxw):
    lines, cur = [], ''
    for ch in s:
        if f.getlength(cur + ch) > maxw and cur: lines.append(cur); cur = ch
        else: cur += ch
    return lines + ([cur] if cur else [])


@fx.effect('chat-drop', 'a chat window slides down behind your head; your request pops in and the reply types itself')
def fx_chat_drop(c, e):
    from PIL import Image, ImageDraw
    W, H = c.W, c.H; u = W / 1080
    ask = e.o.get('ask', '幫我把這支影片加上特效'); reply = e.o.get('text', '好的，九種特效都加好了，影片已經輸出。')
    name = e.o.get('name', 'Claude'); accent = fx.rgb(e.o.get('color'), (217, 119, 87))
    cw = int(W * 0.84); pad = int(40 * u)
    fa, fr, fh = fx.font('uim', 34 * u), fx.font('uim', 36 * u), fx.font('uib', 34 * u)
    ask_lines = _wrap(fa, ask, cw * 0.62); rep_lines = _wrap(fr, reply, cw - 2 * pad - 60 * u)
    lh = 52 * u
    bar = e.o.get('bar', '0') == '1'
    ch = int(pad + 50 * u + len(ask_lines) * lh + 24 * u + 24 * u + len(rep_lines) * lh + (120 * u if bar else 0) + pad * 0.6)
    T = e.d  # stretch the beats to the window
    t_ask, t_dots, t_rep = 0.18 * T, 0.32 * T, 0.45 * T
    k = fx.ease_back(c.lt / min(0.45, 0.2 * T)); out = fx.clamp((e.d - c.lt) / 0.25)
    im = Image.new('RGBA', (cw, ch), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, cw - 1, ch - 1], int(36 * u), fill=(250, 248, 244, 250), outline=(225, 220, 212, 255), width=max(1, int(2 * u)))
    # header
    d.ellipse([pad, pad + 4 * u, pad + 30 * u, pad + 34 * u], fill=accent + (255,))
    d.text((pad + 44 * u, pad + 19 * u), name, font=fh, fill=(40, 38, 34, 255), anchor='lm')
    y = pad + 50 * u
    # the request (right-aligned bubble)
    if c.lt >= t_ask:
        bw = max(fa.getlength(l) for l in ask_lines) + 44 * u; bh = len(ask_lines) * lh + 24 * u
        s = fx.clamp((c.lt - t_ask) / 0.15)
        x1 = cw - pad; x0 = x1 - bw
        d.rounded_rectangle([x0, y, x1, y + bh], int(26 * u), fill=(236, 230, 218, int(255 * s)))
        for i, l in enumerate(ask_lines): d.text((x0 + 22 * u, y + 12 * u + i * lh + lh / 2), l, font=fa, fill=(40, 38, 34, int(255 * s)), anchor='lm')
    y += len(ask_lines) * lh + 24 * u + 24 * u
    # typing dots, then the reply typing out
    if t_dots <= c.lt < t_rep:
        for j in range(3):
            a = 0.35 + 0.65 * (0.5 + 0.5 * __import__('math').sin((c.lt * 9) - j * 0.9))
            cx = pad + 14 * u + j * 30 * u; d.ellipse([cx - 8 * u, y + 18 * u, cx + 8 * u, y + 34 * u], fill=(150, 144, 135, int(255 * a)))
    if c.lt >= t_rep:
        d.ellipse([pad, y + 6 * u, pad + 30 * u, y + 36 * u], fill=accent + (255,))
        total = sum(len(l) for l in rep_lines); shown = int(total * fx.clamp((c.lt - t_rep) / max(0.4, (T - t_rep) * 0.7)))
        for i, l in enumerate(rep_lines):
            part = l[:max(0, shown)]; shown -= len(l)
            if part: d.text((pad + 50 * u, y + 21 * u + i * lh), part, font=fr, fill=(40, 38, 34, 255), anchor='lm')
    # input bar
    by = ch - pad - 70 * u
    if bar: d.rounded_rectangle([pad, by, cw - pad, by + 70 * u], int(35 * u), fill=(255, 255, 255, 255), outline=(225, 220, 212, 255), width=max(1, int(2 * u)))
    if bar: d.text((pad + 30 * u, by + 35 * u), e.o.get('hint', '回覆 Claude⋯'), font=fa, fill=(170, 164, 155, 255), anchor='lm')
    card = fx.shadowed(im, 24, 14, 70)
    top = H * float(e.o['y']) if 'y' in e.o else max(H * 0.01, (c.fy - c.fw * 1.05) - card.height + 24 * 2)
    cy = top + card.height / 2 - (1 - k) * (card.height + top)
    fx.place(c, card, W / 2, cy, 1, 0, out, behind=e.o.get('front', '0') != '1')


# phone mock: a big phone pops up beside the speaker, its screen runs a short chat with steps ticking off
@fx.effect('phone-flat', 'drawn flat phone (fallback for phone-mock)')
def fx_phone_mock(c, e):
    import math
    from PIL import Image, ImageDraw
    W, H = c.W, c.H
    ph = int(H * float(e.o.get('size', 0.44))); pw = int(ph * 0.49); u = pw / 500
    ask = e.o.get('ask', '剪掉前 3 秒，加上字幕')
    steps = [s for s in str(e.o.get('text', '找到開頭空白|剪掉前 3 秒|加上中文字幕')).split('|') if s]
    done = e.o.get('done', '完成'); accent = fx.rgb(e.o.get('color'), (217, 119, 87))
    T = e.d; k = fx.ease_back(c.lt / 0.45); out = fx.clamp((e.d - c.lt) / 0.25)
    im = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, pw - 1, ph - 1], int(70 * u), fill=(28, 28, 32, 255), outline=(120, 120, 128, 255), width=int(5 * u))
    b = int(14 * u); d.rounded_rectangle([b, b, pw - 1 - b, ph - 1 - b], int(58 * u), fill=(16, 16, 18, 255))
    d.rounded_rectangle([pw / 2 - 70 * u, 30 * u, pw / 2 + 70 * u, 70 * u], int(20 * u), fill=(0, 0, 0, 255))
    white, grey = (240, 240, 244, 255), (150, 150, 158, 255)
    f_s, f_m, f_b = fx.font('uim', 26 * u), fx.font('uim', 35 * u), fx.font('uib', 38 * u)
    d.text((60 * u, 50 * u), e.o.get('time', '9:41'), font=f_s, fill=white, anchor='lm')
    d.ellipse([50 * u, 110 * u, 74 * u, 134 * u], fill=accent + (255,))
    d.text((86 * u, 122 * u), e.o.get('name', 'Claude'), font=f_b, fill=white, anchor='lm')
    d.line([40 * u, 160 * u, pw - 40 * u, 160 * u], fill=(50, 50, 56, 255), width=max(1, int(2 * u)))
    y = 190 * u
    t1 = 0.2 * T
    if c.lt > t1:
        a = int(255 * fx.clamp((c.lt - t1) / 0.15)); lines = _wrap(f_m, ask, pw * 0.68)
        bw = max(f_m.getlength(l) for l in lines) + 40 * u; bh = len(lines) * 50 * u + 28 * u
        d.rounded_rectangle([pw - 40 * u - bw, y, pw - 40 * u, y + bh], int(24 * u), fill=accent[:3] + (a,))
        for i, l in enumerate(lines): d.text((pw - 40 * u - bw + 20 * u, y + 14 * u + 25 * u + i * 50 * u), l, font=f_m, fill=(255, 255, 255, a), anchor='lm')
        y += bh + 36 * u
    else:
        y += 100 * u
    for i, s in enumerate(steps):
        ts = 0.32 * T + i * (0.4 * T / max(1, len(steps)))
        if c.lt < ts: break
        a = int(255 * fx.clamp((c.lt - ts) / 0.12)); ok = c.lt > ts + 0.25 * T / len(steps)
        cx, cy = 64 * u, y + 24 * u
        if ok:
            d.ellipse([cx - 16 * u, cy - 16 * u, cx + 16 * u, cy + 16 * u], fill=(52, 199, 89, a))
            d.line([(cx - 8 * u, cy), (cx - 2 * u, cy + 7 * u), (cx + 9 * u, cy - 7 * u)], fill=(255, 255, 255, a), width=int(5 * u))
        else:
            ang = (c.lt * 400) % 360
            d.arc([cx - 16 * u, cy - 16 * u, cx + 16 * u, cy + 16 * u], ang, ang + 270, fill=grey[:3] + (a,), width=int(4 * u))
        d.text((100 * u, cy), s, font=f_m, fill=white[:3] + (a,), anchor='lm'); y += 74 * u
    if c.lt > 0.8 * T:
        s = fx.ease_back((c.lt - 0.8 * T) / 0.25); bw2, bh2 = 240 * u * s, 80 * u * s
        bx, by = pw / 2, ph - 150 * u
        d.rounded_rectangle([bx - bw2 / 2, by - bh2 / 2, bx + bw2 / 2, by + bh2 / 2], int(32 * u * s) + 1, fill=(52, 199, 89, 255))
        if s > 0.6: d.text((bx, by), done, font=f_b, fill=(255, 255, 255, 255), anchor='mm')
    # a soft glare across the glass
    gl = Image.new('RGBA', (pw, ph), (0, 0, 0, 0)); ImageDraw.Draw(gl).polygon([(0, 0), (pw * 0.55, 0), (0, ph * 0.45)], fill=(255, 255, 255, 14))
    im.alpha_composite(gl)
    side = e.o.get('side', 'left'); sgn = 1 if side == 'left' else -1
    card, shadow = _phone_3d(im, float(e.o.get('yaw', 24)), float(e.o.get('pitch', 6)), sgn, c.lt)
    cx = W * (0.2 if side == 'left' else 0.8); cy = H * float(e.o.get('y', 0.42))
    cy += math.sin(c.lt * 2.2) * H * 0.006  # gentle float
    rot = float(e.o.get('tilt', 4)) * sgn
    al = out * fx.clamp(c.lt / 0.12); y = cy + (1 - k) * H * 0.25; s = 0.85 + 0.15 * k
    fx.place(c, shadow, cx + sgn * W * 0.035, y + H * 0.045, s, rot, al * 0.55, behind=True)
    fx.place(c, card, cx, y, s, rot, al, behind=e.o.get('front', '0') != '1', guard=e.o.get('front', '0') == '1')


def _phone_3d(im, yaw, pitch, sgn, t):
    """Turn a flat phone picture into a phone seen at an angle: perspective, a visible metal side, a shadow."""
    import math
    import numpy as np, cv2
    from PIL import Image
    pw, ph = im.size
    F = np.asarray(im, np.float32) / 255
    sy = math.sin(math.radians(yaw)); wf = pw * math.cos(math.radians(yaw))
    dy = ph * 0.5 * sy * 0.32; dxp = pw * math.sin(math.radians(pitch)) * 0.18
    th = pw * 0.07 * sy / 0.4  # side thickness that shows
    pad = int(th + 30); Wc, Hc = int(wf + 2 * pad), int(ph + 2 * pad)
    if sgn == 1:   # near edge on the left, screen turned toward the centre
        dst = [(dxp, 0), (wf - dxp * 0.6, dy), (wf, ph - dy), (0, ph)]
    else:
        dst = [(dxp * 0.6, dy), (wf - dxp, 0), (wf, ph), (0, ph - dy)]
    dst = np.float32([(x + pad, y + pad) for x, y in dst])
    M = cv2.getPerspectiveTransform(np.float32([(0, 0), (pw, 0), (pw, ph), (0, ph)]), dst)
    front = cv2.warpPerspective(F, M, (Wc, Hc), flags=cv2.INTER_LINEAR)
    # metal side along the near edge
    a, b = (dst[0], dst[3]) if sgn == 1 else (dst[1], dst[2])
    off = np.float32([-th * sgn, th * 0.12])
    poly = np.int32([a, b, b + off, a + off])
    side = np.zeros((Hc, Wc, 4), np.float32); cv2.fillPoly(side, [poly], (0.42, 0.42, 0.46, 1.0), lineType=cv2.LINE_AA)
    yy = np.linspace(1.15, 0.75, Hc, dtype=np.float32)[:, None, None]
    side[..., :3] = np.clip(side[..., :3] * yy, 0, 1)
    # side buttons as small bumps
    for f0, f1 in ((0.22, 0.30), (0.34, 0.42)):
        p0 = a + (b - a) * f0; p1 = a + (b - a) * f1
        cv2.line(side, tuple(np.int32(p0 + off * 1.15)), tuple(np.int32(p1 + off * 1.15)), (0.55, 0.55, 0.6, 1.0), max(3, int(th * 0.35)), cv2.LINE_AA)
    al = front[..., 3:4]
    comp = side * (1 - al) + front * al
    comp[..., 3:4] = np.clip(side[..., 3:4] + al, 0, 1)
    # a light sweep across the glass
    xx = np.arange(Wc, dtype=np.float32)[None, :]; yy2 = np.arange(Hc, dtype=np.float32)[:, None]
    sweep = ((t * 0.6) % 1.6 - 0.3) * (Wc + Hc)
    band = np.clip(1 - np.abs(xx + yy2 * 0.6 - sweep) / (Wc * 0.12), 0, 1) * 0.10
    comp[..., :3] = np.clip(comp[..., :3] + band[..., None] * al, 0, 1)
    card = Image.fromarray((comp * 255).astype(np.uint8), 'RGBA')
    sh = cv2.GaussianBlur(comp[..., 3], (0, 0), max(8, Wc * 0.04))
    shadow = np.zeros((Hc, Wc, 4), np.float32); shadow[..., 3] = sh
    return card, Image.fromarray((shadow * 255).astype(np.uint8), 'RGBA')


# phone mock with a real phone picture: the screen animation is warped onto the green screen of assets/phone_mockup.png
def _phone_asset(path, flip):
    import numpy as np, cv2
    from PIL import Image
    src = np.asarray(Image.open(path).convert('RGBA'), np.float32) / 255
    if flip: src = src[:, ::-1].copy()
    rgb = np.ascontiguousarray(src[..., :3]); h, w = rgb.shape[:2]
    if src[..., 3].min() < 0.98:   # a transparent PNG: use its own cut-out
        alpha = src[..., 3]
    else:                          # a white background: cut off near-white pixels connected to the border
        white = (rgb.min(axis=2) > 0.8).astype(np.uint8)
        ff = white.copy(); m2 = np.zeros((h + 2, w + 2), np.uint8)
        for seed in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1)): cv2.floodFill(ff, m2, seed, 2)
        alpha = cv2.GaussianBlur(1 - (ff == 2).astype(np.float32), (0, 0), 1.2)
    # green screen weight, soft at the anti-aliased edge
    g = np.clip((rgb[..., 1] - np.maximum(rgb[..., 0], rgb[..., 2]) - 0.25) / 0.35, 0, 1)
    # remove green spill on the bezel edge (the frame is grey, so this only touches leftover green)
    rgb = rgb.copy(); rgb[..., 1] = np.minimum(rgb[..., 1], np.maximum(rgb[..., 0], rgb[..., 2]) + 0.03)
    ys, xs = np.nonzero(g > 0.5)
    pts = np.stack([xs, ys], 1).astype(np.float32)
    s, d = pts.sum(1), pts[:, 0] - pts[:, 1]
    quad = np.float32([pts[s.argmin()], pts[d.argmax()], pts[s.argmax()], pts[d.argmin()]])  # TL TR BR BL
    # tidy the box to the alpha bounding box
    yy, xx = np.nonzero(alpha > 0.05); x0, x1, y0, y1 = xx.min(), xx.max() + 1, yy.min(), yy.max() + 1
    return rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1], g[y0:y1, x0:x1], quad - np.float32([x0, y0])


def _phone_screen(c, e, sw, sh):
    """The animated screen (no bezel), sw x sh pixels."""
    import math
    from PIL import Image, ImageDraw
    u = sw / 460
    ask = e.o.get('ask', '剪掉前 3 秒加字幕')
    steps = [s for s in str(e.o.get('text', '找到開頭空白|剪掉前 3 秒|加上中文字幕')).split('|') if s]
    done = e.o.get('done', '完成'); accent = fx.rgb(e.o.get('color'), (217, 119, 87)); T = e.d
    im = Image.new('RGBA', (sw, sh), (16, 16, 18, 255)); d = ImageDraw.Draw(im)
    white, grey = (240, 240, 244, 255), (150, 150, 158, 255)
    f_s, f_m, f_b = fx.font('uim', 26 * u), fx.font('uim', 34 * u), fx.font('uib', 38 * u)
    d.text((44 * u, 44 * u), e.o.get('time', '9:41'), font=f_s, fill=white, anchor='lm')
    d.ellipse([36 * u, 112 * u, 62 * u, 138 * u], fill=accent + (255,))
    d.text((76 * u, 125 * u), e.o.get('name', 'Claude'), font=f_b, fill=white, anchor='lm')
    d.line([28 * u, 168 * u, sw - 28 * u, 168 * u], fill=(50, 50, 56, 255), width=max(1, int(2 * u)))
    y = 200 * u
    if c.lt > 0.2 * T:
        a = int(255 * fx.clamp((c.lt - 0.2 * T) / 0.15)); lines = _wrap(f_m, ask, sw * 0.7)
        bw = max(f_m.getlength(l) for l in lines) + 40 * u; bh = len(lines) * 48 * u + 28 * u
        d.rounded_rectangle([sw - 28 * u - bw, y, sw - 28 * u, y + bh], int(24 * u), fill=accent[:3] + (a,))
        for i, l in enumerate(lines): d.text((sw - 28 * u - bw + 20 * u, y + 14 * u + 24 * u + i * 48 * u), l, font=f_m, fill=(255, 255, 255, a), anchor='lm')
        y += bh + 40 * u
    else:
        y += 110 * u
    for i, s in enumerate(steps):
        ts = 0.32 * T + i * (0.4 * T / max(1, len(steps)))
        if c.lt < ts: break
        a = int(255 * fx.clamp((c.lt - ts) / 0.12)); ok = c.lt > ts + 0.25 * T / len(steps)
        cx, cy = 50 * u, y + 24 * u
        if ok:
            d.ellipse([cx - 17 * u, cy - 17 * u, cx + 17 * u, cy + 17 * u], fill=(52, 199, 89, a))
            d.line([(cx - 8 * u, cy), (cx - 2 * u, cy + 7 * u), (cx + 9 * u, cy - 7 * u)], fill=(255, 255, 255, a), width=int(5 * u))
        else:
            ang = (c.lt * 400) % 360
            d.arc([cx - 17 * u, cy - 17 * u, cx + 17 * u, cy + 17 * u], ang, ang + 270, fill=grey[:3] + (a,), width=int(4 * u))
        d.text((84 * u, cy), s, font=f_m, fill=white[:3] + (a,), anchor='lm'); y += 74 * u
    if c.lt > 0.8 * T:
        s = fx.ease_back((c.lt - 0.8 * T) / 0.25); bw2, bh2 = 240 * u * s, 80 * u * s
        bx, by = sw / 2, sh - 150 * u
        d.rounded_rectangle([bx - bw2 / 2, by - bh2 / 2, bx + bw2 / 2, by + bh2 / 2], int(40 * u * s) + 1, fill=(52, 199, 89, 255))
        if s > 0.6: d.text((bx, by), done, font=f_b, fill=(255, 255, 255, 255), anchor='mm')
    return im


@fx.effect('phone-mock', 'a real-looking phone floats beside you at an angle; on its screen a request comes in, steps tick off, then Done')
def fx_phone_real(c, e):
    import math, os
    import numpy as np, cv2
    from PIL import Image
    W, H = c.W, c.H
    side = e.o.get('side', 'left'); flip = side != 'left'
    path = e.o.get('phone', os.path.join(fx.ROOT, 'assets', 'phone_mockup.png'))
    if not os.path.exists(path): return fx.EFFECTS['phone-flat'][0](c, e)
    rgb, alpha, g, quad = fx.cached(e, 'asset', lambda: _phone_asset(path, flip))
    ph = H * float(e.o.get('size', 0.46)); sc = ph / rgb.shape[0]
    sw, sh = 460, int(460 * (np.linalg.norm(quad[3] - quad[0]) / max(1, np.linalg.norm(quad[1] - quad[0]))))
    scr = np.asarray(_phone_screen(c, e, sw, sh), np.float32) / 255
    hh, ww = rgb.shape[:2]
    M = cv2.getPerspectiveTransform(np.float32([(0, 0), (sw, 0), (sw, sh), (0, sh)]), quad)
    warped = cv2.warpPerspective(scr[..., :3], M, (ww, hh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    gg = g[..., None]
    img = rgb * (1 - gg) + warped * gg
    # a slow light sweep over the glass
    xx = np.arange(ww, dtype=np.float32)[None, :]; yy = np.arange(hh, dtype=np.float32)[:, None]
    sweep = ((c.lt * 0.6) % 1.6 - 0.3) * (ww + hh)
    band = np.clip(1 - np.abs(xx + yy * 0.6 - sweep) / (ww * 0.12), 0, 1) * 0.08
    img = np.clip(img + band[..., None] * gg, 0, 1)
    phone = np.dstack([img, alpha])
    pim = Image.fromarray((phone * 255).astype(np.uint8), 'RGBA')
    pim = pim.resize((max(1, int(ww * sc)), max(1, int(hh * sc))), Image.LANCZOS)
    sha = cv2.GaussianBlur(np.asarray(pim, np.float32)[..., 3] / 255, (0, 0), max(6, pim.width * 0.05))
    shadow = Image.fromarray((np.dstack([np.zeros(sha.shape + (3,)), sha]) * 255).astype(np.uint8), 'RGBA')
    k = fx.ease_back(c.lt / 0.45); out = fx.clamp((e.d - c.lt) / 0.25)
    sgn = 1 if side == 'left' else -1
    cx = W * float(e.o.get('x', 0.22 if side == 'left' else 0.78)); cy = H * float(e.o.get('y', 0.42))
    cy += math.sin(c.lt * 2.2) * H * 0.006
    al = out * fx.clamp(c.lt / 0.12); y = cy + (1 - k) * H * 0.25; s = 0.85 + 0.15 * k
    rot = float(e.o.get('tilt', 3)) * sgn
    behind = e.o.get('front', '0') != '1'
    fx.place(c, shadow, cx + sgn * W * 0.03, y + H * 0.04, s, rot, al * 0.5, behind=True)
    fx.place(c, pim, cx, y, s, rot, al, behind=behind, guard=not behind)


def _real_phone(c, e, screen, flip, key='asset'):
    """Real phone picture with `screen` (a PIL image) warped onto its green screen. Returns (phone, shadow) PIL images at asset size."""
    import os
    import numpy as np, cv2
    from PIL import Image
    path = e.o.get('phone', os.path.join(fx.ROOT, 'assets', 'phone_mockup.png'))
    rgb, alpha, g, quad = fx.cached(e, key, lambda: _phone_asset(path, flip))
    hh, ww = rgb.shape[:2]; sw, sh = screen.size
    scr = np.asarray(screen.convert('RGB'), np.float32) / 255
    M = cv2.getPerspectiveTransform(np.float32([(0, 0), (sw, 0), (sw, sh), (0, sh)]), quad)
    warped = cv2.warpPerspective(scr, M, (ww, hh), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    gg = g[..., None]; img = rgb * (1 - gg) + warped * gg
    pim = Image.fromarray((np.dstack([np.clip(img, 0, 1), alpha]) * 255).astype(np.uint8), 'RGBA')
    sha = cv2.GaussianBlur(alpha, (0, 0), max(6, ww * 0.05))
    shadow = Image.fromarray((np.dstack([np.zeros(sha.shape + (3,)), sha]) * 255).astype(np.uint8), 'RGBA')
    return pim, shadow, quad


@fx.effect('phone-orbit', 'a giant phone stands beside you; photo cards burst out of it and spin in a 3D ring above it')
def fx_phone_orbit(c, e):
    import math, os
    from PIL import Image
    W, H = c.W, c.H
    side = e.o.get('side', 'left'); flip = side != 'left'; sgn = 1 if side == 'left' else -1
    if not os.path.exists(e.o.get('phone', os.path.join(fx.ROOT, 'assets', 'phone_mockup.png'))):
        return fx.EFFECTS['orbit'][0](c, e)
    K = int(e.o.get('count', 6)); cw = int(W * float(e.o.get('card', 0.25)))
    cards = fx.cached(e, 'cards', lambda: [fx.card(fx.vary(im, i) if e.o.get('images') is None else im, cw) for i, im in enumerate(e.cards)])
    def scr():
        im = Image.new('RGB', (460, 1000), (16, 16, 18))
        gr = fx.thumb_grid(e.cards, 3, 5, 140, 8, look=False)
        im.paste(gr, ((460 - gr.width) // 2, 120), gr if gr.mode == 'RGBA' else None)
        return im
    screen = fx.cached(e, 'screen', scr)
    phone, shadow, quad = fx.cached(e, 'phone', lambda: _real_phone(c, e, screen, flip))
    ph = H * float(e.o.get('size', 0.72)); sc = ph / phone.height
    k = fx.ease_back(c.lt / 0.45); out = fx.clamp((e.d - c.lt) / 0.25); al = out * fx.clamp(c.lt / 0.12)
    px = W * float(e.o.get('x', 0.3 if side == 'left' else 0.7)); py = H * float(e.o.get('y', 0.6))
    py += math.sin(c.lt * 2.2) * H * 0.005 + (1 - k) * H * 0.2
    s = 0.85 + 0.15 * k; rot = float(e.o.get('tilt', 3)) * sgn + math.sin(c.lt * 3.1) * float(e.o.get('wobble', 2))
    # the ring sits just above the phone's screen top
    top = py - ph * s / 2
    rise = fx.ease_out((c.lt - 0.25) / 0.6)
    ox = px; oy = top + (1 - rise) * ph * 0.35 - H * float(e.o.get('lift', 0.05)) * rise
    rx = W * float(e.o.get('radius', 0.3)) * rise; ry = H * float(e.o.get('ring', 0.09)) * rise
    if e.o.get('clamp', '0') == '1': rx = min(rx, ((px if sgn == 1 else W - px) - cw * 0.55) * rise)
    items = []
    for i in range(K):
        th = i * 2 * math.pi / K + c.lt * float(e.o.get('speed', 1.6))
        items.append((math.sin(th), th, i))
    back = [it for it in items if it[0] < 0]; front = [it for it in items if it[0] >= 0]
    def draw(group):
        for depth, th, i in sorted(group):
            sc2 = (0.6 + 0.45 * (depth + 1) / 2) * (0.35 + 0.65 * rise)
            cd = cards[i % len(cards)]
            sq = max(0.18, abs(math.sin(th)))  # turned edge-on at the sides of the ring
            cd = cd.resize((max(1, int(cd.width * sq)), cd.height), Image.BILINEAR)
            fx.place(c, cd, ox + rx * math.cos(th), oy + ry * math.sin(th), sc2, 0,
                     al * fx.clamp((c.lt - 0.25) / 0.15) * (0.55 + 0.45 * (depth + 1) / 2), behind=True)
    fx.place(c, shadow.resize((max(1, int(shadow.width * sc)), max(1, int(shadow.height * sc)))), px + sgn * W * 0.03, py + H * 0.035, s, rot, al * 0.5, behind=True)
    draw(back)
    fx.place(c, phone.resize((max(1, int(phone.width * sc)), max(1, int(phone.height * sc))), Image.LANCZOS), px, py, s, rot, al, behind=True)
    draw(front)


# phone pop-out: the shot plays inside a big phone, then the speaker jumps out of the screen to full size
@fx.effect('phone-pop', 'the shot plays on a big phone screen, then you jump out of the phone to full size')
def fx_phone_pop(c, e):
    import math
    import numpy as np, cv2
    from PIL import Image
    W, H = c.W, c.H; T = e.d; t = c.lt
    orig = c.img.copy(); m = np.clip(c.m, 0, 1)
    # clean plate: paint the person out (cheap, at quarter size; works best on plain walls)
    q = 4; sm = cv2.resize(orig, (W // q, H // q), interpolation=cv2.INTER_AREA)
    pm = (cv2.resize(m, (W // q, H // q)) > 0.04).astype(np.uint8)
    # light pixels touching the person (white shoes, highlights the matte misses)
    near = cv2.dilate(pm, np.ones((9, 9), np.uint8), iterations=2)
    pm = np.maximum(pm, ((sm.min(axis=2) > 0.78) & (near > 0)).astype(np.uint8))
    mm = cv2.dilate(pm, np.ones((5, 5), np.uint8), iterations=3)
    plate = cv2.inpaint((sm * 255).astype(np.uint8), mm, 9, cv2.INPAINT_TELEA).astype(np.float32) / 255
    plate = cv2.GaussianBlur(cv2.resize(plate, (W, H), interpolation=cv2.INTER_CUBIC), (0, 0), 2)
    mb = cv2.GaussianBlur(cv2.resize(mm.astype(np.float32), (W, H)), (0, 0), 6)[..., None]
    plate = orig * (1 - mb) + plate * mb
    # beats
    t_in, t_pop, t_out = 0.22 * T, 0.5 * T, 0.75 * T
    k_in = fx.ease_back(t / t_in); pop = fx.ease_back((t - t_in) / (t_pop - t_in)) if t > t_in else 0.0
    k_out = fx.ease_inout((t - t_pop) / (t_out - t_pop)) if t > t_pop else 0.0
    done = fx.clamp((t - t_out) / 0.2)
    # the phone: the shot (with the person) on its screen until the jump
    ph = H * float(e.o.get('size', 0.62)); pcx, pcy = W / 2, H * float(e.o.get('y', 0.55))
    pcy += k_out * H * 0.75
    scr_img = Image.fromarray((np.clip(orig if t < t_in else plate, 0, 1) * 255).astype(np.uint8)).resize((460, 818))
    phone, shadow, quad = _real_phone(c, e, scr_img, False, key='asset-pop')
    sc = ph / phone.height
    c.img = plate.copy()
    if k_out < 1:
        fx.place(c, shadow.resize((max(1, int(shadow.width * sc)), max(1, int(shadow.height * sc)))), pcx + W * 0.03, pcy + H * 0.035, 0.6 + 0.4 * k_in, 0, 0.5 * (1 - k_out))
        fx.place(c, phone.resize((max(1, int(phone.width * sc)), max(1, int(phone.height * sc))), Image.LANCZOS), pcx, pcy, 0.6 + 0.4 * k_in, 0, fx.clamp(t / 0.1) * (1 - k_out))
    if t >= t_in:
        # the person scales from the screen's size and centre to full size at the real position
        ys, xs = np.nonzero(m > 0.3)
        if len(xs):
            bx, by = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
            qc = quad.mean(0); qh = np.linalg.norm(quad[3] - quad[0])
            s0 = (qh * sc) / H * 0.9
            s = s0 + (1 - s0) * pop
            sx0, sy0 = pcx + (qc[0] - phone.width / 2) * sc, pcy + (qc[1] - phone.height / 2) * sc
            tx = sx0 + (bx - sx0) * pop; ty = sy0 + (by - sy0) * pop - math.sin(min(1, pop) * math.pi) * H * 0.05
            A = np.float32([[s, 0, tx - s * bx], [0, s, ty - s * by]])
            lay = cv2.warpAffine(np.dstack([orig, m]), A, (W, H), flags=cv2.INTER_LINEAR)
            a = lay[..., 3:4]
            c.img = c.img * (1 - a) + lay[..., :3] * a
    if done > 0: c.img = c.img * (1 - done) + orig * done


# paper collage: the room turns into a cut-paper collage, you become a sticker with a white edge, paper letters pop in
def _torn(points, rng, amp):
    """Densify a polygon and jitter its edge so it looks torn."""
    out = []
    for i in range(len(points)):
        (x0, y0), (x1, y1) = points[i], points[(i + 1) % len(points)]
        n = max(2, int(((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5 / (amp * 3)))
        for j in range(n):
            t = j / n; out.append((x0 + (x1 - x0) * t + rng.uniform(-amp, amp), y0 + (y1 - y0) * t + rng.uniform(-amp, amp)))
    return out


def _pattern(w, h, kind, base, ink, u):
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), base); d = ImageDraw.Draw(im)
    if kind == 'dots':
        st = int(26 * u); r = 7 * u
        for y in range(0, h + st, st):
            for x in range(0, w + st, st):
                ox = st / 2 if (y // st) % 2 else 0
                d.ellipse([x + ox - r, y - r, x + ox + r, y + r], fill=ink)
    elif kind == 'stripes':
        st = int(34 * u)
        for x in range(-h, w + h, st): d.line([(x, 0), (x + h, h)], fill=ink, width=int(12 * u))
    elif kind == 'zigzag':
        st = int(40 * u)
        for y in range(0, h + st, st):
            pts = [(x, y + (st / 3 if (x // st) % 2 else 0)) for x in range(0, w + st, st)]
            d.line(pts, fill=ink, width=int(8 * u))
    return im


@fx.effect('paper-collage', 'the room becomes a cut-paper collage, you become a sticker with a white edge, paper letters pop in')
def fx_paper_collage(c, e):
    import os, random
    import numpy as np, cv2
    from PIL import Image, ImageDraw
    W, H = c.W, c.H; u = W / 1080
    fps_stop = float(e.o.get('stop', 8)); step = int(c.lt * fps_stop)  # stop-motion beats
    def build():
        rng = random.Random(int(e.o.get('seed', 7)))
        bg = Image.new('RGB', (W, H), (250, 244, 232))
        pal = [((255, 92, 140), (255, 210, 225)), ((255, 214, 64), (255, 245, 190)), ((62, 200, 120), (200, 245, 215)),
               ((238, 52, 46), (255, 200, 190)), ((80, 150, 255), (205, 225, 255))]
        kinds = ['dots', 'stripes', 'zigzag', 'dots', 'none', 'stripes', 'dots']
        pieces = []
        for i in range(7):
            base, ink = pal[i % len(pal)]
            cx, cy = rng.uniform(-0.1, 1.1) * W, rng.uniform(0.0, 1.0) * H
            rw, rh = rng.uniform(0.35, 0.7) * W, rng.uniform(0.18, 0.4) * H
            ang = rng.uniform(-0.5, 0.5)
            corners = [(-rw / 2, -rh / 2), (rw / 2, -rh / 2), (rw / 2, rh / 2), (-rw / 2, rh / 2)]
            import math as _m
            poly = [(cx + x * _m.cos(ang) - y * _m.sin(ang), cy + x * _m.sin(ang) + y * _m.cos(ang)) for x, y in corners]
            poly = _torn(poly, rng, 6 * u)
            k = kinds[i % len(kinds)]
            pat = _pattern(W, H, k, ink if k != 'none' else base, base, u) if k != 'none' else Image.new('RGB', (W, H), base)
            pieces.append((poly, pat))
        for poly, pat in pieces:
            m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon(poly, fill=255)
            sh = Image.new('L', (W, H), 0); ImageDraw.Draw(sh).polygon([(x + 8 * u, y + 10 * u) for x, y in poly], fill=90)
            bg.paste((0, 0, 0), (0, 0), sh.filter(__import__('PIL.ImageFilter', fromlist=['x']).GaussianBlur(10 * u)))
            bg.paste(pat, (0, 0), m)
        arr = np.asarray(bg, np.float32) / 255
        tex_path = e.o.get('paper', os.path.join(fx.ROOT, 'assets', 'paper_texture.png'))
        if os.path.exists(tex_path):
            tex = np.asarray(Image.open(tex_path).convert('L').resize((W, H)), np.float32) / 255
            tex = 0.82 + 0.18 * (tex / max(1e-3, tex.mean()))
        else:
            n = np.random.default_rng(3).normal(0, 1, (H // 2, W // 2)).astype(np.float32)
            tex = 1 + 0.035 * cv2.resize(cv2.GaussianBlur(n, (0, 0), 1.2), (W, H))
        return np.clip(arr * tex[..., None], 0, 1)
    bg = fx.cached(e, 'collage', build)
    rng = np.random.default_rng(step)
    jx, jy = rng.uniform(-3, 3, 2) * u  # tiny stop-motion wobble
    k = fx.clamp(c.lt / 0.35); out = fx.clamp((e.d - c.lt) / 0.25)
    orig = c.img.copy(); m = np.clip(c.m, 0, 1)
    # wipe the collage in from the left in stop-motion steps
    edge = W * (int(k * 4) / 4 if k < 1 else 1)
    reveal = (np.arange(W)[None, :] < edge).astype(np.float32)[..., None] * out
    M = np.float32([[1, 0, jx], [0, 1, jy]])
    bgj = cv2.warpAffine(bg, M, (W, H), borderMode=cv2.BORDER_REFLECT)
    canvas = orig * (1 - reveal) + bgj * reveal
    # sticker: white edge and a soft shadow around the person
    pm = (m > 0.4).astype(np.uint8)
    ring = cv2.dilate(pm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (int(26 * u) | 1, int(26 * u) | 1))).astype(np.float32)
    ring = cv2.GaussianBlur(ring, (0, 0), 1.5)[..., None] * reveal
    shad = cv2.GaussianBlur(np.roll(np.roll(ring[..., 0], int(12 * u), 0), int(10 * u), 1), (0, 0), 10 * u)[..., None] * 0.35
    canvas = canvas * (1 - shad)
    canvas = canvas * (1 - ring) + ring  # white
    canvas = canvas * (1 - m[..., None]) + orig * m[..., None]
    c.img = canvas
    # paper letters pop in one by one along the top
    txt = e.o.get('text', 'PAPER')
    chars = [ch for ch in txt if ch.strip()]
    if chars:
        n = len(chars); size = min(W * 0.2, W * 0.86 / n)
        pal = [(238, 52, 46), (255, 255, 255), (30, 30, 34), (255, 214, 64), (62, 200, 120)]
        for i, ch in enumerate(chars):
            t0 = 0.25 + i * 0.12
            if c.lt < t0: break
            r = random.Random(i * 31 + 5)
            col = pal[i % len(pal)]; fg = (255, 255, 255) if col in [(238, 52, 46), (30, 30, 34), (62, 200, 120)] else (30, 30, 34)
            tile = fx.cached(e, f'tile{i}', lambda ch=ch, col=col, fg=fg, r=r: _paper_tile(ch, size, col, fg, r, u))
            x = W * 0.07 + size * 0.55 + i * size * 0.98; y = H * float(e.o.get('y', 0.1)) + r.uniform(-0.25, 0.25) * size * 0.4
            rot = r.uniform(-9, 9) + (rng.uniform(-1.5, 1.5) if step % 2 else 0)
            sc = 1.25 - 0.25 * fx.clamp((c.lt - t0) / 0.12)
            fx.place(c, tile, x + jx, y + jy, sc, rot, out, behind=True)


def _paper_tile(ch, size, col, fg, r, u):
    from PIL import Image, ImageDraw, ImageFilter
    f = fx.font('anton', size * 0.82)
    w = int(size * 0.95); h = int(size * 1.15)
    im = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    poly = _torn([(20, 20), (20 + w, 20), (20 + w, 20 + h), (20, 20 + h)], r, 3 * u)
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).polygon([(x + 6, y + 8) for x, y in poly], fill=(0, 0, 0, 110))
    im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)))
    d.polygon(poly, fill=col + (255,))
    d.text((20 + w / 2, 20 + h / 2), ch, font=f, fill=fg + (255,), anchor='mm')
    return im


# headline cards: messages from everywhere pile up behind you, faster and faster, until the wall is about to overflow
_PILE = [
    ('news', 'Claude 一句話剪出[九宮格]特效', '科技新報 · 台北'), ('social', 'wait, this was edited by Claude??', '@alex.makes · LA'),
    ('sticky', '不用剪輯軟體', ''), ('black', 'ONE PROMPT', ''), ('comment', '求教學！！', '@小芸 · 台中'),
    ('news', '動画編集、もう[アプリ]いらない？', '日経クロストレンド · Tokyo'), ('mono', '> render done · 4K', ''),
    ('social', '零基礎也能[上手]，我試了', '@阿哲 · 高雄'), ('sticky', '一句話就好', ''), ('black', '九種特效', ''),
    ('comment', 'How?!', '@maya · London'), ('news', 'Creators are [ditching] editing apps', 'The Verge · New York'),
    ('social', 'え、これ全部AI？', '@みき · Osaka'), ('mono', '$ claude /effects', ''), ('sticky', 'CapCut 做很久', ''),
    ('comment', '教練我想學', '@Ivy · 香港'), ('black', 'NO TIMELINE', ''), ('news', '剪輯師[3 分鐘]下班', '數位時代 · 台北'),
    ('social', 'no keyframes. none.', '@ken.edits · Sydney'), ('sticky', '人物自動摳好', ''), ('comment', '神作', '@小美 · 新竹'),
    ('mono', '> effects: 9 / 9', ''), ('news', '[中文]字型也能用', '自由時報 · 台南'), ('black', 'FULL REEL', ''),
    ('social', 'saved this for later', '@jules · Paris'), ('comment', 'すごい', '@yuta · 京都'), ('sticky', '免費開源', ''),
    ('news', '一支影片，[九種]特效', 'INSIDE · 台北'), ('comment', '怎麼做的？', '@Leo · 新加坡'), ('black', '爆款', ''),
    ('social', 'my editor is shaking rn', '@sam · Toronto'), ('sticky', '我的九宮格', ''), ('mono', '> cutout ok', ''),
    ('comment', 'Need this', '@nina · Berlin'),
]


def _pile_card(kind, text, src, W, rng):
    from PIL import Image, ImageDraw
    u = W / 1080; s = rng.uniform(0.95, 1.9)
    def marked(d, f, txt, x, y, fill, lh):
        plain = txt.replace('[', '').replace(']', ''); on = False; xx = x
        for ch in txt:
            if ch == '[': on = True; continue
            if ch == ']': on = False; continue
            wch = f.getlength(ch)
            if on: d.rectangle([xx - 1, y + lh * 0.42, xx + wch + 1, y + lh * 0.95], fill=(255, 226, 64, 255))
            xx += wch
        d.text((x, y), plain, font=f, fill=fill)
    if kind == 'news':
        f = fx.font('didoneb', 40 * u * s); cw = int(min(W * 0.62, f.getlength(text.replace('[', '').replace(']', '')) + 56 * u * s))
        ch = int(f.size * 1.4 + 70 * u * s); im = Image.new('RGBA', (cw, ch), (246, 242, 232, 255)); d = ImageDraw.Draw(im)
        d.line([22 * u * s, 18 * u * s, cw - 22 * u * s, 18 * u * s], fill=(20, 20, 20, 255), width=max(1, int(2 * u)))
        marked(d, f, text, 24 * u * s, 26 * u * s, (18, 18, 18, 255), f.size * 1.3)
        d.text((24 * u * s, ch - 30 * u * s), src, font=fx.font('uim', 20 * u * s), fill=(110, 105, 95, 255))
    elif kind == 'social':
        f = fx.font('uim', 30 * u * s); cw = int(min(W * 0.6, max(f.getlength(text.replace('[', '').replace(']', '')), 200 * u * s) + 60 * u * s))
        ch = int(110 * u * s); im = fx.rrect(cw, ch, 18 * u * s, (255, 255, 255, 255)); d = ImageDraw.Draw(im)
        hue = rng.choice([(255, 140, 120), (120, 170, 255), (130, 210, 160), (220, 150, 255)])
        d.ellipse([18 * u * s, 16 * u * s, 50 * u * s, 48 * u * s], fill=hue + (255,))
        d.text((60 * u * s, 32 * u * s), src, font=fx.font('uib', 20 * u * s), fill=(90, 90, 96, 255), anchor='lm')
        marked(d, f, text, 20 * u * s, 58 * u * s, (20, 20, 24, 255), f.size * 1.3)
    elif kind == 'sticky':
        col = rng.choice([(255, 232, 92), (255, 176, 196), (170, 230, 255), (190, 245, 170)])
        f = fx.font('hand', 44 * u * s); side = int(max(200 * u * s, f.getlength(text) * 0.6))
        im = Image.new('RGBA', (side, side), col + (255,)); d = ImageDraw.Draw(im)
        lines = _wrap(f, text, side - 30 * u * s)
        for i, ln in enumerate(lines): d.text((side / 2, side / 2 + (i - (len(lines) - 1) / 2) * f.size * 1.2), ln, font=f, fill=(30, 30, 30, 255), anchor='mm')
    elif kind == 'comment':
        f = fx.font('uib', 34 * u * s); tw = f.getlength(text); cw = int(tw + 50 * u * s); ch = int(f.size * 1.6 + 44 * u * s)
        col = rng.choice([(10, 132, 255), (233, 233, 238)]); fg = (255, 255, 255) if col[0] < 100 else (20, 20, 24)
        im = fx.rrect(cw, ch, ch * 0.4, col + (255,)); d = ImageDraw.Draw(im)
        d.text((cw / 2, ch * 0.42), text, font=f, fill=fg + (255,), anchor='mm')
        d.text((cw / 2, ch - 16 * u * s), src, font=fx.font('uim', 16 * u * s), fill=fg + (180,), anchor='mm')
    elif kind == 'black':
        f = fx.font('anton', 64 * u * s); cw = int(f.getlength(text) + 50 * u * s); ch = int(f.size * 1.35)
        im = Image.new('RGBA', (cw, ch), (16, 16, 16, 255)); ImageDraw.Draw(im).text((cw / 2, ch / 2), text, font=f, fill=(255, 255, 255, 255), anchor='mm')
    else:  # mono
        f = fx.font('mono', 28 * u * s); cw = int(f.getlength(text) + 40 * u * s); ch = int(f.size * 2)
        im = fx.rrect(cw, ch, 10 * u * s, (18, 24, 22, 255)); ImageDraw.Draw(im).text((20 * u * s, ch / 2), text, font=f, fill=(120, 255, 160, 255), anchor='lm')
    return fx.shadowed(im, 10, 6, 100)


@fx.effect('headline-cards', 'messages from everywhere pile up behind you, faster and faster, until the wall is about to overflow')
def fx_headline_cards(c, e):
    import random
    W, H = c.W, c.H
    if e.o.get('text'):
        items = [('news' if i % 3 == 0 else 'social' if i % 3 == 1 else 'sticky', t, '') for i, t in enumerate(str(e.o['text']).split('|')) if t]
    else:
        n = int(e.o.get('count', len(_PILE) * 2)); items = [_PILE[i % len(_PILE)] for i in range(n)]
    N = len(items)
    cards = fx.cached(e, 'pile', lambda: [_pile_card(k, t, src, W, random.Random(i * 17 + 3)) for i, (k, t, src) in enumerate(items)])
    def layout():
        out = []
        for i in range(N):
            r = random.Random(i * 29 + 5)
            x = r.uniform(-0.08, 1.08) * W
            y = (r.uniform(-0.02, 0.7) if r.random() < 0.75 else r.uniform(0.7, 0.98)) * H
            out.append((x, y, r.uniform(-13, 13)))
        return out
    pos = fx.cached(e, 'pos', layout)
    T = e.d * float(e.o.get('fill', 0.9)); out = fx.clamp((e.d - c.lt) / 0.2)
    for i in range(N):
        t0 = T * ((i / max(1, N - 1)) ** 0.55)   # gaps shrink: the pile speeds up
        if c.lt < t0: break
        x, y, rot = pos[i]; k = fx.ease_back((c.lt - t0) / 0.18)
        fx.place(c, cards[i], x, y, 0.4 + 0.6 * k, rot, out * fx.clamp((c.lt - t0) / 0.05), behind=True)


# crayon doodle: a boiling white crayon outline around you, plus a crayon heart, star, sparkles and excitement marks
def _crayon_layer(H, W, draw_fn, step):
    import numpy as np, cv2
    from PIL import Image, ImageDraw
    im = Image.new('L', (W, H), 0); draw_fn(ImageDraw.Draw(im))
    a = np.asarray(im, np.float32) / 255
    rng = np.random.default_rng(step)
    grain = (rng.random((H // 2, W // 2)) > 0.22).astype(np.float32)
    grain = cv2.resize(grain, (W, H), interpolation=cv2.INTER_NEAREST)
    return a * (0.55 + 0.45 * grain)


@fx.effect('crayon-doodle', 'a wobbly white crayon outline traces you, with a crayon heart, star, sparkles and excitement marks')
def fx_crayon_doodle(c, e):
    import math
    import numpy as np, cv2
    W, H = c.W, c.H; u = W / 1080
    step = int(c.lt * float(e.o.get('boil', 8)))
    rng = np.random.default_rng(step + 101)
    out = fx.clamp((e.d - c.lt) / 0.25); k = fx.clamp(c.lt / 0.25)
    # outline: the person's silhouette pushed out a little, redrawn with a hand wobble
    m = (c.m > 0.4).astype(np.uint8)
    off = int(W * float(e.o.get('gap', 0.022)))
    big = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * off + 1, 2 * off + 1)))
    cs, _ = cv2.findContours(big, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    lw = max(4, int(W * float(e.o.get('width', 0.007))))
    def outline(d):
        for cnt in cs:
            if len(cnt) < 40: continue
            pts = cnt[::6, 0, :].astype(np.float32)
            pts += rng.normal(0, 1.6 * u, pts.shape).astype(np.float32)
            d.line([tuple(p) for p in pts] + [tuple(pts[0])], fill=255, width=lw, joint='curve')
    a = _crayon_layer(H, W, outline, step) * k * out
    white = np.ones((H, W, 3), np.float32)
    fx.comp(c, np.dstack([white, a]), 0, 0, 1, behind=True)
    # doodles around the head, in crayon colours
    sz = max(c.fw, W * 0.09) * float(e.o.get('size', 1.0))
    def doodle(t0, colour, fn):
        if c.lt < t0: return
        kk = fx.ease_back((c.lt - t0) / 0.25)
        lay = _crayon_layer(H, W, lambda d: fn(d, kk), step + int(t0 * 10))
        rgb = np.empty((H, W, 3), np.float32); rgb[:] = np.float32(colour) / 255
        fx.comp(c, np.dstack([rgb, lay * out]), 0, 0, 1, behind=True)
    fx_, fy_ = c.fx, c.fy
    def heart(d, kk):
        cx, cy, r = fx_ - sz * 1.75, fy_ + sz * 0.35, sz * 0.42 * kk
        if r < 2: return
        d.ellipse([cx - r, cy - r * 0.9, cx, cy + r * 0.1], fill=255); d.ellipse([cx, cy - r * 0.9, cx + r, cy + r * 0.1], fill=255)
        d.polygon([(cx - r * 0.97, cy - r * 0.25), (cx + r * 0.97, cy - r * 0.25), (cx, cy + r * 1.05)], fill=255)
    def star(d, kk):
        cx, cy, r = fx_ + sz * 1.75, fy_ + sz * 0.05, sz * 0.45 * kk
        if r < 2: return
        pts = [(cx + (r if i % 2 == 0 else r * 0.45) * math.cos(-math.pi / 2 + i * math.pi / 5), cy + (r if i % 2 == 0 else r * 0.45) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
        d.polygon(pts, fill=255)
    def sparkles(d, kk):
        for sx, sy, sr in ((-2.1, -0.9, 0.18), (-1.4, 1.2, 0.13), (2.2, -1.2, 0.16), (2.3, 1.0, 0.12), (-0.9, -1.7, 0.1)):
            cx, cy, r = fx_ + sz * sx, fy_ + sz * sy, sz * sr * kk
            if r < 1: continue
            d.polygon([(cx, cy - r), (cx + r * 0.25, cy - r * 0.25), (cx + r, cy), (cx + r * 0.25, cy + r * 0.25), (cx, cy + r), (cx - r * 0.25, cy + r * 0.25), (cx - r, cy), (cx - r * 0.25, cy - r * 0.25)], fill=255)
    def marks(d, kk):
        bx, by = fx_ + sz * 1.25, fy_ - sz * 1.35
        for j, ang in enumerate((-60, -35, -10)):
            a_ = math.radians(ang); L = sz * 0.38 * kk; x0, y0 = bx + j * sz * 0.22, by + j * sz * 0.12
            d.line([(x0, y0), (x0 + L * math.cos(a_), y0 + L * math.sin(a_))], fill=255, width=max(4, int(W * 0.007)))
    doodle(0.15, fx.rgb(e.o.get('heart'), (250, 110, 150)), heart)
    doodle(0.3, fx.rgb(e.o.get('star'), (255, 222, 70)), star)
    doodle(0.45, (255, 255, 255), sparkles)
    doodle(0.55, fx.rgb(e.o.get('star'), (255, 222, 70)), marks)


# magazine cover: editorial typography only, black or white, no outlines or shadows; the masthead sits behind your head
def _type(text, kind, size, col, track=0.0):
    """Plain text image, optional letter-spacing (track, in em). No stroke, no shadow."""
    from PIL import Image, ImageDraw
    f = fx.font(kind, size)
    if track <= 0:
        bb = f.getbbox(text); im = Image.new('RGBA', (bb[2] - bb[0] + 4, bb[3] - bb[1] + 4), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((2 - bb[0], 2 - bb[1]), text, font=f, fill=col + (255,)); return im
    gap = size * track; w = sum(f.getlength(ch) for ch in text) + gap * max(0, len(text) - 1)
    asc, desc = f.getmetrics(); im = Image.new('RGBA', (int(w) + 4, asc + desc + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = 2
    for ch in text: d.text((x, 2), ch, font=f, fill=col + (255,)); x += f.getlength(ch) + gap
    return im


def _vtype(text, kind, size, col, gap=0.08):
    """Vertical text, one character under another (for Chinese editorial headlines)."""
    from PIL import Image, ImageDraw
    f = fx.font(kind, size); step = size * (1 + gap)
    im = Image.new('RGBA', (int(size * 1.15), int(step * len(text) + size * 0.2)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for i, ch in enumerate(text): d.text((im.width / 2, size * 0.55 + i * step), ch, font=f, fill=col + (255,), anchor='mm')
    return im


@fx.effect('magazine-cover', 'you become an editorial magazine cover: big serif masthead behind your head, cover lines in black or white')
def fx_magazine_cover(c, e):
    W, H = c.W, c.H; u = W / 1080
    ink = (255, 255, 255) if e.o.get('color', 'black') == 'white' else (14, 14, 14)
    mast = e.o.get('text', 'STUDIO')
    kicker = e.o.get('kicker', '封面故事')
    heads = [x for x in str(e.o.get('lines', '一句話|剪出一支片')).split('|') if x]
    sub = e.o.get('sub', '不用剪輯師也不用軟體')
    right = [x for x in str(e.o.get('right', 'Claude|親手剪的')).split('|') if x]
    issue = e.o.get('issue', '2026 · 十一月號 · NO.11'); foot = e.o.get('foot', 'AI EDIT')
    def build():
        # masthead fitted to the width
        size = int(W * 0.3)
        while fx.font('didoneb', size).getlength(mast) > W * 0.9 and size > 40: size = int(size * 0.96)
        el = {'mast': _type(mast, 'didoneb', size, ink), 'issue': _type(issue, 'uim', 24 * u, ink, 0.18),
              'kicker': _type(kicker, 'uim', 24 * u, ink, 0.35),
              'heads': [_vtype(h, 'didoneb', 92 * u, ink) for h in heads],
              'sub': _vtype(sub, 'uim', 26 * u, ink, 0.12), 'foot': _type(foot, 'uim', 22 * u, ink, 0.4),
              'right': [_type(r, 'didonei' if i == 0 else 'didoneb', (58 if i == 0 else 64) * u, ink) for i, r in enumerate(right)]}
        return el
    el = fx.cached(e, 'type', build)
    out = fx.clamp((e.d - c.lt) / 0.3)
    def show(im, x, y, t0, anchor='l', behind=True):
        if c.lt < t0: return
        k = fx.ease_out((c.lt - t0) / 0.35); a = out * fx.clamp((c.lt - t0) / 0.25)
        cx = x + im.width / 2 if anchor == 'l' else (x - im.width / 2 if anchor == 'r' else x)
        fx.place(c, im, cx, y + im.height / 2 + (1 - k) * 18 * u, 1, 0, a, behind=behind)
    # a gentle editorial grade (slightly warm, slightly more contrast)
    g = fx.clamp(c.lt / 0.4) * out * 0.5
    if g > 0: c.img = c.img * (1 - g) + fx.np.clip((c.img - 0.5) * 1.08 + 0.5 + fx.np.float32([0.012, 0.004, -0.01]), 0, 1) * g
    m = el['mast']; top = H * float(e.o.get('top', 0.035))
    show(el['issue'], W / 2, top, 0.05, 'c')
    # masthead: its lower part goes behind the head
    my = max(top + el['issue'].height + 10 * u, (c.fy - c.fw * 0.9) - m.height * 0.62)
    show(m, W / 2, my, 0.0, 'c')
    # vertical headlines, read right to left, in the column left of the body
    x0 = W * 0.06; y = H * float(e.o.get('y', 0.4))
    show(el['kicker'], x0, y, 0.35); y += el['kicker'].height + 22 * u
    xr_col = x0 + sum(h.width for h in el['heads']) + 4 * u * len(el['heads'])
    xx = xr_col
    for i, h in enumerate(el['heads']):
        xx -= h.width; show(h, xx, y, 0.45 + i * 0.12); xx -= 4 * u
    show(el['sub'], xr_col + 10 * u, y + 8 * u, 0.75)
    xr = W * 0.935; yr = H * 0.76
    for i, r in enumerate(el['right']):
        show(r, xr, yr, 0.9 + i * 0.1, 'r'); yr += r.height + 4 * u
    show(el['foot'], x0, H * 0.955 - el['foot'].height, 1.1)


fx.CARD_FX = tuple(fx.CARD_FX) + ('phone-orbit',)

if __name__ == '__main__':
    fx.main()
