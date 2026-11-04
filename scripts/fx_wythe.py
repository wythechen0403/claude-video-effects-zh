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


@fx.effect('phone-orbit', 'photo cards rise out of a floating phone and spin in a ring above it')
def fx_phone_orbit(c, e):
    import math, os
    from PIL import Image
    W, H = c.W, c.H
    side = e.o.get('side', 'left'); flip = side != 'left'; sgn = 1 if side == 'left' else -1
    if not os.path.exists(e.o.get('phone', os.path.join(fx.ROOT, 'assets', 'phone_mockup.png'))):
        return fx.EFFECTS['orbit'][0](c, e)
    K = int(e.o.get('count', 5)); cw = int(W * float(e.o.get('card', 0.11)))
    cards = fx.cached(e, 'cards', lambda: [fx.card(fx.vary(im, i) if e.o.get('images') is None else im, cw) for i, im in enumerate(e.cards)])
    def scr():
        im = Image.new('RGB', (460, 1000), (16, 16, 18))
        gr = fx.thumb_grid(e.cards, 3, 5, 140, 8, look=False)
        im.paste(gr, ((460 - gr.width) // 2, 120), gr if gr.mode == 'RGBA' else None)
        return im
    screen = fx.cached(e, 'screen', scr)
    phone, shadow, quad = fx.cached(e, 'phone', lambda: _real_phone(c, e, screen, flip))
    ph = H * float(e.o.get('size', 0.30)); sc = ph / phone.height
    k = fx.ease_back(c.lt / 0.45); out = fx.clamp((e.d - c.lt) / 0.25); al = out * fx.clamp(c.lt / 0.12)
    px = W * float(e.o.get('x', 0.19 if side == 'left' else 0.81)); py = H * float(e.o.get('y', 0.58))
    py += math.sin(c.lt * 2.2) * H * 0.005 + (1 - k) * H * 0.2
    s = 0.85 + 0.15 * k; rot = float(e.o.get('tilt', 3)) * sgn
    # the ring sits just above the phone's screen top
    top = py - ph * s / 2
    rise = fx.ease_out((c.lt - 0.25) / 0.6)
    ox = px; oy = top + (1 - rise) * ph * 0.35 - H * 0.07 * rise
    rx = min(W * float(e.o.get('radius', 0.15)), (px if sgn == 1 else W - px) - cw * 0.55) * rise; ry = H * 0.045 * rise
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


fx.CARD_FX = tuple(fx.CARD_FX) + ('phone-orbit',)

if __name__ == '__main__':
    fx.main()
