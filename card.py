# card.py — 마일스톤 카드 (색 추출 + 무드 분기 + 곡별 오버라이드)

import io
import os
import colorsys
import requests
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _hex(s):
    s = s.strip().lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _load_thumb(video_id):
    urls = [
        f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
        f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
    ]
    for url in urls:
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200 and len(r.content) > 3000:
                return Image.open(io.BytesIO(r.content)).convert("RGB")
        except Exception:
            continue
    raise RuntimeError(f"썸네일 로드 실패: {video_id}")


def _cover(img, w, h):
    src, dst = img.width / img.height, w / h
    if src > dst:
        nh, nw = h, int(h * src)
    else:
        nw, nh = w, int(w / src)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


# ---------- ① 색 추출 ----------

def _palette(img, n=6):
    small = img.resize((80, 80))
    pal = small.convert("P", palette=Image.ADAPTIVE, colors=n)
    raw = pal.getpalette()
    return [
        (count, tuple(raw[idx * 3: idx * 3 + 3]))
        for count, idx in sorted(pal.getcolors(), reverse=True)
    ]


def _sat_val(rgb):
    r, g, b = [c / 255 for c in rgb]
    _, s, v = colorsys.rgb_to_hsv(r, g, b)
    return s, v


def _pick_accent(palette):
    best, best_score = (245, 196, 81), -1
    for count, rgb in palette:
        s, v = _sat_val(rgb)
        if v < 0.30:
            continue
        score = s * 1.6 + v * 0.6
        if score > best_score:
            best_score, best = score, rgb
    return best


def _dominant_pair(palette):
    if not palette:
        return (40, 40, 55), (15, 15, 25)
    top = palette[0][1]

    def hue(rgb):
        r, g, b = [c / 255 for c in rgb]
        return colorsys.rgb_to_hsv(r, g, b)[0]

    th, second, best_d = hue(top), top, -1
    for count, rgb in palette[1:]:
        d = abs(hue(rgb) - th)
        d = min(d, 1 - d)
        if d > best_d:
            best_d, second = d, rgb
    return top, second


def _scale(rgb, f):
    return tuple(max(0, min(255, int(c * f))) for c in rgb)


def _brightness(img):
    g = img.convert("L").resize((64, 64))
    px = list(g.getdata())
    return sum(px) / len(px) / 255.0        # 0~1


def _lin_gradient(size, horizontal, a0, a1, edge):
    w, h = size
    if horizontal:
        line = Image.new("L", (w, 1)); px = line.load()
        for x in range(w):
            t = min(1.0, (x / w) / edge) if edge > 0 else 1.0
            px[x, 0] = int(a0 + (a1 - a0) * t)
    else:
        line = Image.new("L", (1, h)); px = line.load()
        for y in range(h):
            t = min(1.0, (y / h) / edge) if edge > 0 else 1.0
            px[0, y] = int(a0 + (a1 - a0) * t)
    return line.resize((w, h))


def make_milestone_card(video_id, title, artist, views_text, out_path,
                        song_type="", card_opts=None):
    W, H = 1600, 900
    MX, MB, GAP = 96, 96, 24
    card_opts = card_opts or {}

    base = _cover(_load_thumb(video_id), W, H)

    # ① 색 추출
    palette = _palette(base)
    dom, sub = _dominant_pair(palette)
    accent = _pick_accent(palette)

    # ③ 곡별 오버라이드
    if card_opts.get("accent"):
        accent = _hex(card_opts["accent"])
    if card_opts.get("tint"):
        dom = _hex(card_opts["tint"])

    # ② 무드: 밝은 썸네일일수록 스크림 진하게 (흰 글자 가독성 확보)
    bright = _brightness(base)
    left_a = int(150 + bright * 90)          # 150~240
    bot_a = int(115 + bright * 80)

    # 검정 대신 '곡의 색'으로 스크림 (왼쪽=주요색, 아래=보조색)
    tint_left = Image.new("RGB", (W, H), _scale(dom, 0.22)) # 0.22 클 수록 밝음(색이 칙칙한 경우)
    tint_bot = Image.new("RGB", (W, H), _scale(sub, 0.20))
    base = Image.composite(tint_left, base, _lin_gradient((W, H), True, left_a, 0, 0.72)) # left_a 스크림 진하기(글자 안 보일 때)
    base = Image.composite(tint_bot, base, _lin_gradient((W, H), False, 0, bot_a, 0.5))

    draw = ImageDraw.Draw(base)

    f_num = _font("Pretendard-ExtraBold.otf", 200)
    f_unit = _font("Pretendard-Bold.otf", 82)
    f_title = _font("Pretendard-Bold.otf", 74)
    f_artist = _font("Pretendard-Medium.otf", 44)
    f_badge = _font("Pretendard-Bold.otf", 32)

    white, soft = (255, 255, 255), (232, 232, 232)

    if "만" in views_text:
        num_part, unit_part = views_text.split("만")[0], "만"
    else:
        num_part, unit_part = views_text, ""

    def asc(font):
        return font.getmetrics()[0]

    # 아래에서 위로 쌓기
    y = H - MB
    draw.text((MX, y), artist, font=f_artist, fill=soft, anchor="ls")

    y -= asc(f_artist) + GAP
    draw.text((MX, y), title, font=f_title, fill=white, anchor="ls")

    y -= asc(f_title) + GAP + 8
    draw.text((MX, y), num_part, font=f_num, fill=white, anchor="ls")
    if unit_part:
        nw = draw.textlength(num_part, font=f_num)
        draw.text((MX + nw + 14, y), unit_part, font=f_unit, fill=white, anchor="ls")

    # 배지: tagline(오버라이드) > song_type
    badge_text = card_opts.get("tagline") or song_type
    if badge_text:
        y -= asc(f_num) + GAP + 6
        r = 10
        draw.ellipse((MX, y - r * 2, MX + r * 2, y), fill=accent)
        draw.text((MX + r * 2 + 16, y), badge_text, font=f_badge, fill=soft, anchor="ls")


    # 특별 카드 테두리 (100만·1000만 등)
    if card_opts.get("frame"):
        m = 34
        draw.rectangle([m, m, W - m, H - m], outline=accent, width=3)


    base.save(out_path, "PNG")
    return out_path
