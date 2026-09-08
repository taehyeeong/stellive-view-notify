"""
특별 마일스톤 카드(100만/1000만) 렌더러.

card_special.html 템플릿에 곡 데이터를 채워 넣고, Playwright(크로미움)로
스크린샷을 찍어 PNG로 저장한다. CSS 그대로 렌더되므로 폰트/블러/그라데이션이
목업과 100% 동일하게 나온다.

사용:
    from render_card import make_special_card
    make_special_card("rQaluJS-Tc0", "하나(夏拏)", "시라유키 히나",
                      "/tmp/card.png", milestone=1_000_000)
"""

import os
import io
import html
import uuid
import base64
import pathlib
import urllib.request

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "fonts")
TEMPLATE = os.path.join(HERE, "card_special.html")

# (CSS font-family 이름, fonts/ 파일명, weight) — 없는 파일은 자동 skip.
# 브라우저가 글자별로 알아서 폴백해서 한글/한자/일본어/수학볼드/기호/이모지 다 나옴.
_FONTS = [
    ("Pretendard",          "Pretendard-ExtraBold.otf",     800),
    ("Pretendard",          "Pretendard-Bold.otf",          700),
    ("Pretendard",          "Pretendard-Medium.otf",        500),
    ("STIX Two Math",       "STIXTwoMath-Regular.otf",      400),
    ("Noto Sans Symbols2",  "NotoSansSymbols2-Regular.ttf", 400),
    ("Noto Sans CJK KR",    "NotoSansCJKkr-Bold.otf",       700),
    ("Noto Color Emoji",    "NotoColorEmoji.ttf",           400),
]

# 렌더 해상도 (4:5 세로 — 트위터/텔레그램에서 위아래 안 잘림). 실제 픽셀은 2배.
_VIEW_W, _VIEW_H = 1080, 1350
_SCALE = 2


def _font_faces():
    """fonts/ 안의 폰트를 상대경로로 연결하는 @font-face 규칙 생성.
    (임시 HTML을 레포 루트에 쓰므로 'fonts/파일' 상대경로가 안전하게 로드됨)"""
    rules = []
    for family, filename, weight in _FONTS:
        path = os.path.join(FONT_DIR, filename)
        if not os.path.exists(path):
            continue
        ext = filename.rsplit(".", 1)[-1].lower()
        fmt = "opentype" if ext == "otf" else "truetype"
        rules.append(
            "@font-face{font-family:'%s';font-weight:%d;font-style:normal;"
            "src:url('fonts/%s') format('%s');}" % (family, weight, filename, fmt)
        )
    return "\n".join(rules)


def _download_thumb(video_id):
    """maxres → sddefault → hqdefault 순으로 시도. PIL 이미지 반환."""
    last = None
    for quality in ("maxresdefault", "sddefault", "hqdefault"):
        url = "https://img.youtube.com/vi/%s/%s.jpg" % (video_id, quality)
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            data = urllib.request.urlopen(req, timeout=15).read()
            img = Image.open(io.BytesIO(data)).convert("RGB")
            last = img
            if img.size[0] >= 480:   # 유효한 썸네일
                return img
        except Exception:
            continue
    return last


def _accent(img):
    """썸네일에서 채도 높은 대표색을 뽑아 글로우용 hex로 반환."""
    small = img.resize((64, 64))
    pal = small.convert("P", palette=Image.ADAPTIVE, colors=8).convert("RGB")
    counts = pal.getcolors(64 * 64) or []
    best, best_score = None, -1.0
    total = float(64 * 64)
    for count, (r, g, b) in counts:
        mx, mn = max(r, g, b), min(r, g, b)
        val = mx / 255.0
        sat = 0.0 if mx == 0 else (mx - mn) / mx
        if not (0.28 <= val <= 0.97) or sat < 0.25:
            continue
        score = sat * 0.75 + (count / total) * 0.25
        if score > best_score:
            best_score, best = score, (r, g, b)
    if best is None:
        best = (243, 185, 58)  # 폴백: 웜 골드
    # 글로우로 쓰기 좋게 살짝 밝힘
    r, g, b = best
    factor = max(1.0, 210.0 / max(r, g, b, 1))
    best = tuple(min(255, int(c * factor)) for c in (r, g, b))
    return "#%02x%02x%02x" % best


def _split_number(milestone):
    """1_000_000 -> ('100','만'), 10_000_000 -> ('1000','만')"""
    man = int(round(milestone / 10000))
    return str(man), "만"


def make_special_card(video_id, title, artist, out_path,
                      milestone=1_000_000, accent=None):
    """특별 카드를 렌더해 out_path(PNG)에 저장하고 경로를 반환."""
    img = _download_thumb(video_id)
    if img is None:
        raise RuntimeError("썸네일 다운로드 실패: %s" % video_id)

    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=90)
    thumb_uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    if accent is None:
        accent = _accent(img)

    num_main, num_unit = _split_number(milestone)

    with open(TEMPLATE, encoding="utf-8") as f:
        page = f.read()

    page = (page
            .replace("{{FONT_FACES}}", _font_faces())
            .replace("{{THUMB}}", thumb_uri)
            .replace("{{ARTIST}}", html.escape(artist))
            .replace("{{SONG}}", html.escape(title))
            .replace("{{ACCENT}}", accent)
            .replace("{{NUM_MAIN}}", html.escape(num_main))
            .replace("{{NUM_UNIT}}", html.escape(num_unit)))

    # 폰트를 상대경로로 로드하려면 HTML이 레포 루트(fonts/ 옆)에 있어야 함
    tmp_path = os.path.join(HERE, ".card_tmp_%s.html" % uuid.uuid4().hex)
    with open(tmp_path, "w", encoding="utf-8") as tf:
        tf.write(page)

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--allow-file-access-from-files"])
            pg = browser.new_page(
                viewport={"width": _VIEW_W, "height": _VIEW_H},
                device_scale_factor=_SCALE,
            )
            pg.goto(pathlib.Path(tmp_path).as_uri())
            pg.wait_for_timeout(350)   # 폰트/이미지/자동축소 스크립트 완료 대기
            pg.screenshot(path=out_path, type="jpeg", quality=92)
            browser.close()
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    return out_path


if __name__ == "__main__":
    # 로컬 테스트
    make_special_card("rQaluJS-Tc0", "하나(夏拏)", "시라유키 히나",
                      "special_test.png", milestone=1_000_000)
    print("saved special_test.png")
