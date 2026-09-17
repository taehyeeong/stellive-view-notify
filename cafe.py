# cafe.py — 네이버 카페 자동 글쓰기 (전송 전담)
# 반환: {"outcome": "ok"|"failed"|"unknown"|"dry", "articleId": int|None}
#   ok      = 등록 확인됨
#   failed  = 확실히 실패(안 올라감) → 다음 실행 재시도 가능
#   unknown = 결과 불명(타임아웃 등) → 재시도 금지, 수동 확인
import os
import requests
import unicodedata

NAVER_CLIENT_ID     = os.environ.get("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.environ.get("NAVER_CLIENT_SECRET", "")
NAVER_REFRESH_TOKEN = os.environ.get("NAVER_REFRESH_TOKEN", "")
CAFE_CLUB_ID = os.environ.get("CAFE_CLUB_ID", "")
CAFE_MENU_ID = os.environ.get("CAFE_MENU_ID", "")


def cafe_ready():
    return all([NAVER_CLIENT_ID, NAVER_CLIENT_SECRET, NAVER_REFRESH_TOKEN,
                CAFE_CLUB_ID, CAFE_MENU_ID])


def _enc(s):
    s = unicodedata.normalize("NFC", s or "")     # 분해된 자모 재결합
    return s.encode("cp949", "ignore")            # euc-kr → cp949


def _access_token():
    r = requests.get("https://nid.naver.com/oauth2.0/token", params={
        "grant_type": "refresh_token",
        "client_id": NAVER_CLIENT_ID,
        "client_secret": NAVER_CLIENT_SECRET,
        "refresh_token": NAVER_REFRESH_TOKEN,
    }, timeout=10)
    r.raise_for_status()
    tok = r.json().get("access_token")
    if not tok:
        raise RuntimeError(f"access_token 없음: {r.text[:200]}")
    return tok

def _emoji_to_html(s):
    s = unicodedata.normalize("NFC", s or "")
    out = []
    for ch in s:
        try:
            ch.encode("cp949")                    # euc-kr → cp949
            out.append(ch)
        except UnicodeEncodeError:
            out.append(f"&#{ord(ch)};")           # 이모지 등은 HTML 코드로
    return "".join(out)


def post_to_cafe(subject, content, headid=None, image_path=None, dry_run=False):
    if not subject or not content:
        print("⚠️ 제목/본문 비어있음 — 스킵")
        return {"outcome": "failed", "articleId": None}
    if dry_run:
        print(f"[DRY-RUN] 제목:{subject} | 말머리:{headid} | 본문:{content[:100]}")
        return {"outcome": "dry", "articleId": None}
    if not cafe_ready():
        print("⚠️ 카페 설정 미완 — 스킵")
        return {"outcome": "failed", "articleId": None}


    # 토큰 발급 실패 = 아직 아무것도 안 올라감 → failed(재시도 가능)
    try:
        token = _access_token()
    except Exception as e:
        print(f"⚠️ 토큰 갱신 실패: {e}")
        return {"outcome": "failed", "articleId": None}

    url = f"https://openapi.naver.com/v1/cafe/{CAFE_CLUB_ID}/menu/{CAFE_MENU_ID}/articles"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    files = {
        "subject": (None, _enc(_emoji_to_html(subject))),
        "content": (None, _enc(_emoji_to_html(content))),
    }


    if headid is not None and str(headid) not in ("", "0"):
        files["headid"] = (None, str(headid))
    fh = None
    if image_path and os.path.exists(image_path):
        fh = open(image_path, "rb")
        files["image[0]"] = ("card.jpg", fh, "image/jpeg")

    # 요청 자체가 예외(타임아웃 등) = 올라갔는지 불명 → unknown(재시도 금지)
    try:
        r = requests.post(url, headers=headers, files=files, timeout=20)
    except Exception as e:
        print(f"⚠️ 카페 요청 예외(결과 불명): {e}")
        return {"outcome": "unknown", "articleId": None}
    finally:
        if fh:
            fh.close()

    # 응답은 받았음 → 성공 여부 명확히 판정
    try:
        body = r.json()
        article_id = (body.get("message", {}).get("result", {}) or {}).get("articleId")
    except Exception:
        article_id = None
    if r.ok and article_id is not None:
        print(f"✅ 카페 등록 성공 articleId={article_id}")
        return {"outcome": "ok", "articleId": article_id}
    print(f"⚠️ 카페 등록 실패: HTTP {r.status_code} {r.text[:300]}")
    return {"outcome": "failed", "articleId": None}
