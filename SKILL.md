---
name: effects-zh
description: Traditional Chinese edition (繁體中文版) of claude-video-effects. Add any of 51+ video effects to a talking-head video (orbit, spotlight, glass widgets, timeline, checklist, headline wall, comment box, phone fan, liquid glass graph, match-cut, iPhone toggles, LED sign, over-the-shoulder zoom, iMessage pop-ups, place-in-grid and more). Effects track the speaker's face and can sit behind their head. Use when the user types /effects, names one of the effects, or asks to add an effect, zoom, grade, sticker or animation to their video.
---

# Effects (繁體中文版): 51 starter video effects by @vibha.in.progress, with Traditional Chinese text and extra effects by @lady_yang_yung

The user is usually not technical. Keep replies short and friendly, do the work for them, and never ask them to run commands themselves.

All paths below are relative to this skill's folder (the folder this SKILL.md is in). Use its absolute path in commands.

## 1. First run: set up (once)
Run `bash scripts/setup.sh`. It prints `READY` when done (the first time takes 1 to 3 minutes).
- `NEED_FFMPEG`: install it for them. On a Mac: `brew install ffmpeg` (if `brew` is missing, tell them to install Homebrew from brew.sh first). On Windows: `winget install ffmpeg`.
- `NEED_PYTHON`: install Python 3.12 (Mac: `brew install python@3.12`, Windows: `winget install Python.Python.3.12`), then run setup again.
- On Windows, the Python is at `.venv\Scripts\python.exe` instead of `.venv/bin/python`.

## 2. Get the video and the effect
- Video: the user drags the file into the chat, or gives a path. A vertical phone video works best.
- Effect: from `/effects <name>`, or from what they describe. Match their words to the table below. Unsure? Show them the list.

## 3. Find the timing
- If they say "on the word X" or "when I say ...", run `.venv/bin/python scripts/words.py <video>` and use those times.
- If they give no timing, apply the effect for the whole clip, or ask which part (one short question).
- Short windows look best: 1.5 to 4 seconds per effect.

## 4. Draft, check, render
1. Write the plan next to their video as `<video-name>_effects.json`:
   ```json
   {"effects": [
     {"fx": "orbit", "start": 3.2, "end": 6.0},
     {"fx": "backdrop-word", "start": 14.0, "end": 16.3, "text": "CLAUDE"}
   ]}
   ```
2. Check frames first (fast): `.venv/bin/python scripts/fx_wythe.py --plan <plan.json> <video> <folder>/check.png --still 4.5,15.2`, using the middle of each effect. Look at the PNGs yourself. Fix the text, timing or options if something looks off (covers the face, cut off by the edge, unreadable).
3. Render: `.venv/bin/python scripts/fx_wythe.py --plan <plan.json> <video> <video-name>_effects.mp4`. The output keeps their original audio. It renders at 1080p by default; add `--width 2160` for 4K (slower).
4. Tell them where the file is. Remind them in one line to watch it before posting: it drafts, they approve.

Always run `scripts/fx_wythe.py` (never `scripts/fx.py` directly): it takes the same commands, draws Chinese text with Noto Sans TC, and adds the extra effects below.

A single effect needs no plan: `.venv/bin/python scripts/fx_wythe.py orbit <video> <out.mp4> --start 3 --end 6 --text "..." --opt key=value`.

## The 51 effects
| # | `fx` name | What it does | Options (all optional) |
|---|---|---|---|
| 1 | `noise` | Reels pile up behind your head, one every quarter second | `images` (folder of screenshots or clips), `size` |
| 2 | `lineup` | Numbered tiles fan out in an arc above your head | `text` (tile names joined with `\|`) |
| 3 | `locked-on` | Corner brackets snap onto your face, the camera follows you | `zoom` (default 1.35), `text` (tag) |
| 4 | `orbit` | Your reels circle your head: in front at the bottom, behind at the top | `images`, `count`, `speed`, `size` |
| 5 | `lean-in` | A fast punch-in on one word | `zoom` (default 1.45, max 2), `speed` |
| 6 | `backdrop-word` | A giant word drops in behind you | `text`, `color` (hex), `font` (`bold` or `serif`) |
| 7 | `spotlight` | Kills the lights, keeps you lit | `text` (glowing word behind you), `color`, `push` |
| 8 | `the-bill` | Prints your instructions like a receipt into the wall above your head | `text` (lines joined with `\|`) |
| 9 | `moody` | A moody colour grade | `grade` (`moody`, `bw`, `warm`, `cool`, `pop`) |
| 10 | `swipe` | A before and after slider sweeps across you | `grade` (the "after" look) |
| 11 | `todo` | A checklist card beside your head ticks off as you talk | `text` (items with `\|`), `ticks` (video seconds with `\|`), `title` |
| 12 | `comment-box` | An Instagram comment bar types a word and posts it | `text` (default EFFECTS) |
| 13 | `tap` | A Follow button pops up and flips to Following | `at` (video second of the flip), `x`, `y` (0 to 1), `color` |
| 14 | `pause-point` | Freezes the frame and points at you with a hand-drawn arrow | `text` (label), `color`, `label_x` |
| 15 | `uninstall` | A glitchy uninstall bar breaks the frame apart | `text` |
| 16 | `reel-frame` | Your video shrinks into an Instagram reel card | `text` (handle) |
| 17 | `shortcut-rain` | Keyboard keys rain down behind you | `text` (keys with `\|`), `count` |
| 18 | `reject-stamp` | A big red stamp slams onto the screen | `text`, `color`, `angle`, `y` |
| 19 | `countdown-flip` | A 3, 2, 1 flip clock above your head | `from` |
| 20 | `rabbit-hole` | The frame tunnels into itself, spinning | `ratio`, `speed`, `spin` |
| 21 | `cover-star` | You become a magazine cover, title behind your head | `text` (title), `lines` (with `\|`), `issue`, `color` |
| 22 | `scribble` | Marker doodles draw themselves around you | `text` (label), `color` |
| 23 | `glass-widgets` | Frosted glass widgets and mini artifacts float around your head, plus an Edited by Claude pill | `text` (big number), `name`, `handle`, `look` (`simple` for the 3-widget version) |
| 24 | `red-collage` | Black and white you, a giant red word behind, three lines slam in | `text` (red word), `lines` (with `\|`), `tag` |
| 25 | `split-headline` | A headline card slides down and pushes you to the bottom half | `text` (lines with `\|`), `hl` (highlighted word), `pill` |
| 26 | `pastel-word` | Lavender room, giant word behind you, a profile card gets followed | `text`, `name`, `handle` |
| 27 | `check-pills` | Grid-paper room, reel boards behind you, a cursor clicks blue pills | `text` (pills with `\|`), `images` |
| 28 | `timeline` | A dark red film grade with an editing timeline, a REC timecode and a glowing playhead | `text` (title), `sub`, `tc` |
| 29 | `headline-box` | A punch-in with a two-line headline, the second line in a white box | `text` (lines with `\|`), `zoom` |
| 30 | `profile-wall` | Your reels grid fills the wall behind you while a counter ticks up | `images`, `count`, `label` |
| 31 | `tier-list` | A tier list drops in and Claude flies into S tier | `title`, `item`, `others` |
| 32 | `broll-split` | B-roll on top with a price-tag sticker, you below | `images`, `text` (tag) |
| 33 | `phone-fan` | Your reels fan out like a hand of phones under a headline | `images`, `text` (lines with `\|`) |
| 34 | `dot-reveal` | Your shot builds out of glowing dots, then snaps to the full picture | `color`, `cell` |
| 35 | `headline-wall` | Your own headlines pile up behind your head, then a total pops in front | `text` (`headline::meta\|...`), `total`, `label` |
| 36 | `checklist` | A Claude task list under your chin: each step spins, then ticks green | `text` (`step::meta\|...`), `title` |
| 37 | `liquid-glass-graph` | A liquid glass card under your chin: a green graph climbs while the number counts up | `text` (label), `from`, `to` (e.g. `197K`, `59%`), `color` |
| 38 | `carousel-spin` | Your reels spin around you in a 3D carousel, then slow to a stop | `images`, `count`, `size`, `turns` |
| 39 | `match-cut` | News pages cut on one word, locked in a red box behind your head | `text` (the word, default Claude), `color` |
| 40 | `apple-toggles` | An iPhone settings card under your chin flips its switches on, one line at a time | `text` (rows with `\|`), `ticks` (seconds with `\|`), `color` |
| 41 | `led-sign` | The lights drop and a glowing LED sign types itself out behind you | `text` (lines with `\|`), `color`, `push` |
| 42 | `slow-push` | A slow cinematic push-in to your face while the room melts out of focus | `zoom` (default 1.6), `blur` |
| 43 | `over-the-shoulder-zoom` | The camera pushes into one top corner and a see-through liquid glass graph pops beside your head (line climbs, number counts up), pulls back, then the other corner with a second, related bar graph. Your head stays in front | `text` (two labels with `\|`), `to` (two numbers with `\|`, e.g. `197K\|672K`), `zoom` (default 2.0) |
| 44 | `messages` | iMessage notifications pop in one after another, creamy glass with a soft glow, stacking up above the bottom of the frame | `text` (messages with `\|`), `title` (default Messages), `y` |
| 45 | `place-in-grid` | You shrink into the centre tile of your 3x3 profile grid on frosted glass, then 8 reels pop in around you, one per frame, with Instagram view counts on every tile | `images` (folder of your reels or covers), `views` (9 counts with `\|`, the 9th is yours) |
| 46 | `tape-label` | A level strip of yellow tape with your line lands on your chest, kept off your face | `text` |
| 47 | `select-resize` | A blue selection box with handles grabs your number above your head and a cursor drags it bigger | `text` (default 2X) |
| 48 | `wave-trim` | A dark panel above your head shows your voice; the red dotted silence on both ends collapses until only your words are left | none |
| 49 | `huge-strike` | One huge serif word wipes in behind your head, then a red line crosses it out | `text`, `at` (seconds into the effect when the strike lands, default 0.6) |
| 50 | `crayon-write` | A red crayon writes your word behind your head, then underlines it and flies off | `text` |
| 51 | `fan-build` | Your reel covers deal into a fan behind your head, one card at a time | `images` (folder of your covers), `count` (default 13) |

**Named looks** (same effect, a fancier look; they don't add to the count):
- `glitter-spotlight` = `spotlight` with `look=sparkle`: the room goes dark, golden rays burst from behind your head, a big gold word with a shine sweep, twinkling sparkles and a glow around you. `text` (the word), `color`, `push`.
- `cover-star` with `look=editorial`: a soft warm film look, a classic serif masthead behind your head, an issue line and elegant cover lines. `text` (masthead), `issue`, `lines` (3 lines with `\|`), `right` (lines with `\|`), `color`, `accent`, `lines_y`, `right_y`.
- `liquid-glass-graph` with `look=bento`: the climbing graph moves to a smoked glass screen behind your head, with glass bento tiles in front of you (a donut, a KPI, bars). `text`, `from`, `to`, `donut` (`29%::label`), `kpi` (`672K::label`), `bars` (`197\|140\|124::label`).
- `apple-toggles` now sits above you, tucked behind your head, with a gentle zoom (`pos=below` for the old under-the-chin card; `overlap`, `zoom`).

Aliases work too: `bill`, `to-do`, `follow`, `stamp`, `countdown`, `cover`, `rain`, `pause`.

## Extras in this edition (fx_wythe.py)
- **Chinese text**: write Chinese straight into `text`, `title`, `lines` and other text options. Talk to the user in Traditional Chinese when they write in Chinese.
- `profile-wall` option `card_y` (0 to 1): moves the front glass card, e.g. `card_y=0.6` for full-body shots so the card sits mid-frame instead of at the feet.
- `glass-widgets` option `pill_y` (0 to 1): moves the "Edited by Claude" pill, e.g. `pill_y=0.6`.
- `tier-glass`: the tier list on see-through liquid glass, title just above the board (works for close-ups with no room above the head). Options as `tier-list`: `title`, `item`, `others`.
- `scribble-track`: a hand-drawn ring that follows an object (a product, a cup, a book), with an arrow and a label. Steps:
  1. Save the first frame of the effect (`ffmpeg -ss <start> -i <video> -frames:v 1 first.png`) and look at it to find the object's box in pixels.
  2. `.venv/bin/python scripts/track_object.py <video> track.json --box X,Y,W,H --at <start> --check track_check.jpg`, then look at `track_check.jpg`. If the box drifts off the object, try a tighter box or a clearer start frame once.
  3. Effect options: `track=track.json`, `text` (label), `color`, `pad` (ring size, default 1.12).
- `glass-text`: a giant see-through glass word behind the speaker, light bends through the letters and a light sweep passes over. Options: `text`, `y` (0 to 1), `font` (default `anton`; Chinese uses Noto Sans TC), `tint`, `refract`. Best on plain walls.
- `glow-chart`: a glowing line chart draws itself across the frame while a big number counts up; the room dims a little (not the person) so the glow reads. Options: `to` (e.g. `+320%`), `text` (label under the number), `values` (points with `|`), `color`, `dim`, `draw` (seconds to draw the line). Time it to a raised hand.
- `chat-drop`: a cream chat window springs down into the space above the head; the request bubble pops in, typing dots, then the reply types out. Options: `ask`, `text` (reply), `name`, `color`, `y`, `bar=1` (adds an input bar; makes the card taller). Needs headroom above the head.
- `phone-mock`: a real phone picture (`assets/phone_mockup.png`, transparent PNG or white background, screen pure green #00FF00) floats beside the speaker at an angle; the screen animation is warped onto its green screen: request bubble, steps spin then tick, then a Done button. Options: `ask`, `text` (steps with `|`), `done`, `side` (`left`/`right`), `x`, `y`, `size`, `phone` (another mockup path), `front=1`. Falls back to `phone-flat` (a drawn phone) when the picture is missing. To change the phone, generate a new mockup with a pure green screen and replace the file.
- `paper-collage`: the room turns into a cut-paper collage (torn coloured paper, halftone dots, stripes, zigzags) that wipes in with a stop-motion feel; the speaker becomes a sticker with a white edge; paper letters pop in along the top one by one. Options: `text` (the letters; Chinese works), `y`, `seed` (another collage layout), `stop` (stop-motion frames per second, default 8), `paper` (a paper texture image; uses `assets/paper_texture.png` when present).
- `phone-pop` (experimental): the shot plays on a big phone, then the speaker jumps out to full size. It paints the speaker out of the background, which leaves visible marks on textured floors; use `reel-frame` when that shows.
- `phone-orbit`: a giant phone (taller than the speaker) stands beside them, wobbling a little; photo cards burst out of it and spin in a 3D ring above it, edge-on at the sides. Anything that overlaps the speaker goes behind them. Needs the speaker in the right third of the frame (or `side=right` for a speaker on the left). A plain-wall clip with the speaker centred can be shifted: mirror a strip of wall in on the left with ffmpeg (`crop` + `hflip` + `hstack`), avoiding any corner labels. Options: `size` (0.72), `x`, `y`, `card` (0.25), `radius` (0.3), `ring` (0.09), `lift` (0.05), `count` (6), `speed`, `wobble` (2), `clamp=1` (keep the ring inside the frame), `images` (folder of your own photos).
- `headline-cards`: messages from everywhere pile up behind the speaker, faster and faster, until the wall is about to overflow: newspaper clippings, social posts, sticky notes, comment bubbles, black headline cards and terminal lines, in Chinese, English and Japanese, with place tags, many sizes and fonts. `text` replaces the pool with your own lines (`|`); `[bracketed]` words get a yellow marker; `count`, `fill`.
- `magazine-cover`: an editorial magazine cover in black or white type only (no outlines, no shadows): a big serif masthead behind the head, vertical Chinese headlines in Noto Serif TC down the left, a vertical sub line, an italic credit bottom right, issue line on top. Options: `text` (masthead), `lines` (headlines with `|`), `kicker`, `sub`, `right` (`|`), `issue`, `foot`, `color` (`black`/`white`), `y`.
- `crayon-doodle`: a boiling white crayon outline traces the speaker (follows every move), with a crayon heart, star, sparkles and excitement marks around the head. Options: `gap`, `width`, `size`, `boil` (redraws per second), `heart`, `star` (colours).
- Chinese text in serif fonts (`didone*`, `serif`) uses Noto Serif TC automatically; other fonts use Noto Sans TC.
- Names and handles on cards (`name`, `handle` in `glass-widgets`, `profile-wall`, `pastel-word`) default to the original author's. Ask the user for theirs.

## Custom tweaks: try, check, adjust once, then fall back
When the user asks for a change the options don't cover (move something, restyle a card), make it in a separate file like `fx_wythe.py` (never edit `fx.py`). Then:
1. Render check frames and look at them.
2. If it fails, adjust once and check again.
3. If it still fails, use the stock effect instead and tell the user plainly what didn't work.

## Rules
- A `TypeError: 'NoneType' object is not callable` traceback from mediapipe at the very end of a run is harmless cleanup noise: if `saved ...` or `Done:` was printed, the output is fine.
- Never cover the face. Everything either goes behind the person or avoids the face by itself; if a check frame still shows text over the face, move it (`x`, `y`) or shorten the text.
- Effects run in the order listed. Put camera effects (`locked-on`, `lean-in`, `spotlight`) first when they overlap others.
- Zoom never goes past 2x, so the video stays sharp.
- This skill adds visuals only. Sound effects and captions are up to the user (CapCut works well).
- These are starter versions. Be honest about that if the user compares them to a reel they saw.
