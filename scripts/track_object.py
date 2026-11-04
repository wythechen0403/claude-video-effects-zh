#!/usr/bin/env python3
"""Follow one object (a product, a cup, a book...) through a video, for scribble-track.

  python scripts/track_object.py in.mp4 track.json --box X,Y,W,H [--at 0] [--check check.jpg]

--box   the object's box in pixels on the frame at --at seconds (x, y = top-left corner).
        Find it by looking at that frame first (e.g. save it with ffmpeg and open it).
--check saves 5 frames with the tracked box drawn on them. Look at it before rendering:
        if the box drifts off the object, pick a clearer start frame or a tighter box.
Output: JSON rows [seconds, x0, y0, x1, y1] with coordinates as 0-1 fractions of the frame.
"""
import argparse, json
import cv2

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('out')
ap.add_argument('--box', required=True); ap.add_argument('--at', type=float, default=0.0)
ap.add_argument('--check')
a = ap.parse_args()

cap = cv2.VideoCapture(a.video); fps = cap.get(cv2.CAP_PROP_FPS) or 30
cap.set(cv2.CAP_PROP_POS_MSEC, a.at * 1000)
ok, fr = cap.read()
if not ok: raise SystemExit('could not read the start frame')
H, W = fr.shape[:2]
x, y, w, h = (int(float(v)) for v in a.box.split(','))
tr = cv2.TrackerCSRT_create(); tr.init(fr, (x, y, w, h))
t = a.at; rows = [[t, x / W, y / H, (x + w) / W, (y + h) / H]]
while True:
    ok, fr = cap.read()
    if not ok: break
    t += 1 / fps; ok2, b = tr.update(fr)
    if ok2: rows.append([round(t, 3), b[0] / W, b[1] / H, (b[0] + b[2]) / W, (b[1] + b[3]) / H])
json.dump(rows, open(a.out, 'w'))
print(f'tracked {len(rows)} frames -> {a.out}')

if a.check:
    cap = cv2.VideoCapture(a.video); outs = []
    for k in range(5):
        r = rows[min(len(rows) - 1, k * (len(rows) - 1) // 4)]
        cap.set(cv2.CAP_PROP_POS_MSEC, r[0] * 1000); ok, fr = cap.read()
        if not ok: continue
        cv2.rectangle(fr, (int(r[1] * W), int(r[2] * H)), (int(r[3] * W), int(r[4] * H)), (0, 255, 255), max(3, W // 150))
        outs.append(cv2.resize(fr, (W // 3, H // 3)))
    if outs: cv2.imwrite(a.check, cv2.hconcat(outs)); print('check image ->', a.check)
