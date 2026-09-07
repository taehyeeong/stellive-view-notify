# card.py — 마일스톤 축하 카드 생성 (풀블리드 스타일)

import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def _font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)


def _load_thumb(video_id):
    """화질 좋은 썸네일부터 시도해서 로드."""
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
    """비율 유지하며 w×h를 꽉 채우도록 center-crop."""
    src = img.width / img.height
    dst = w / h
    if src > dst:
        nh, nw = h, int(h * src)
    else:
        nw, nh = w, int(w / src)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - w) // 2, (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _lin_gradient(size, horizontal, a0, a1, edge):
    """단방향 알파 그라데이션 마스크."""
    w, h = size
    if horizontal:
        line = Image.new("L", (w, 1))
        px = line.load()
        for x in range(w):
            t = min(1.0, (x / w) / edge) if edge > 0 else 1.0
            px[x, 0] = int(a0 + (a1 - a0) * t)
    else:
        line = Image.new("L", (1, h))
        px = line.load()
        for y in range(h):
            t = min(1.0, (y / h) / edge) if edge > 0 else 1.0
            px[0, y] = int(a0 + (a1 - a0) * t)
    return line.resize((w, h))


def _apply_scrim(img):
    w, h = img.size
    black = Image.new("RGB", (w, h), (0, 0, 0))
    img = Image.composite(black, img, _lin_gradient((w, h), False, 0, 165, 0.58))  # 아래
    img = Image.composite(black, img, _lin_gradient((w, h), True, 180, 0, 0.72))   # 왼쪽
    return img


def make_milestone_card(video_id, title, artist, views_text, out_path):
    W, H = 1600, 900
    MX, MB, GAP = 96, 96, 24                # 여백·줄간격 (조정 가능)

    img = _apply_scrim(_cover(_load_thumb(video_id), W, H))
    draw = ImageDraw.Draw(img)

    f_num    = _font("Pretendard-ExtraBold.otf", 200)
    f_unit   = _font("Pretendard-Bold.otf", 82)
    f_title  = _font("Pretendard-Bold.otf", 74)
    f_artist = _font("Pretendard-Medium.otf", 44)

    white, soft = (255, 255, 255), (232, 232, 232)

    if "만" in views_text:
        num_part, unit_part = views_text.split("만")[0], "만"
    else:
        num_part, unit_part = views_text, ""

    def asc(font):
        return font.getmetrics()[0]

    # 아래에서 위로 쌓기 (anchor='ls' = 왼쪽 baseline)
    y = H - MB
    draw.text((MX, y), artist, font=f_artist, fill=soft, anchor="ls")

    y -= asc(f_artist) + GAP
    draw.text((MX, y), title, font=f_title, fill=white, anchor="ls")

    y -= asc(f_title) + GAP + 8
    draw.text((MX, y), num_part, font=f_num, fill=white, anchor="ls")
    if unit_part:
        nw = draw.textlength(num_part, font=f_num)
        draw.text((MX + nw + 14, y), unit_part, font=f_unit, fill=white, anchor="ls")

    

    img.save(out_path, "PNG")
    return out_path
