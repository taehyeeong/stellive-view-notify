# cafe.py — 네이버 카페 API 글쓰기
# 테스트로 확인한 방식: 제목/본문 UTF-8 URL 인코딩, 이미지 필드명 "image"
# 연달아 올리면 999 "게시글을 연속으로 등록할 수 없습니다" → 60초 간격은 통과
import os
import urllib.parse
import requests

NAVER_CLIENT_ID     = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
NAVER_REFRESH_TOKEN = os.environ.get("NAVER_REFRESH_TOKEN", "")
CAFE_CLUB_ID = os.environ.get("CAFE_CLUB_ID", "")
CAFE_MENU_ID = os.environ.get("CAFE_MENU_ID", "")


def cafe_ready():
    return all([NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_REFRESH_TOKEN,
                CAFE_CLUB_ID, CAFE_MENU_ID])


def _token():
    r = requests.get("https://nid.naver.com/oauth2.0/token", params={
        "grant_type": "refresh_token", "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET, "refresh_token": NAVER_REFRESH_TOKEN,
    }, timeout=10)
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError(r.text[:200])
    return tok


def post_to_cafe(subject, content, headid=None, image_path=None):
    """반환: {"ok": 성공, "url": 글 주소, "busy": 연속 등록 제한, "msg": 오류 내용}"""
    try:
        token = _token()
    except Exception as e:
        return {"ok": False, "url": None, "busy": False, "msg": f"토큰 갱신 실패: {e}"}

    url = f"https://openapi.naver.com/v1/cafe/{CAFE_CLUB_ID}/menu/{CAFE_MENU_ID}/articles"
    data = {"subject": urllib.parse.quote(subject),
            "content": urllib.parse.quote(content)}
    if headid not in (None, "", 0, "0"):
        data["headid"] = str(headid)
    fh = open(image_path, "rb") if image_path and os.path.exists(image_path) else None
    files = [("image", ("card.jpg", fh, "image/jpeg"))] if fh else None
    try:
        r = requests.post(url, headers={"Authorization": f"Bearer {token}"},
                          data=data, files=files, timeout=30)
    except Exception as e:
        return {"ok": False, "url": None, "busy": False, "msg": f"요청 예외(등록 여부 불명): {e}"}
    finally:
        if fh:
            fh.close()

    try:
        msg = r.json().get("message", {})
    except Exception:
        msg = {}
    result = msg.get("result") or {}
    if r.ok and result.get("articleId"):
        return {"ok": True, "url": result.get("articleUrl"), "busy": False, "msg": ""}
    err = msg.get("error") or {}
    text = err.get("message") or err.get("msg") or r.text[:300]
    return {"ok": False, "url": None, "busy": "연속" in text,
            "msg": f"HTTP {r.status_code} {text}"}