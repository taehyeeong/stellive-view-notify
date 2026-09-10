import dataclasses
import os
import json
import requests
import re
import time
import random

from datetime import datetime, timezone, timedelta, date
from render_card import make_special_card
from requests import RequestException
from dotenv import load_dotenv
from urllib.parse import quote



class QuotaExceededError(Exception):
    pass


def main():
    global _current_key_index, _current_oauth_index
    _current_key_index, _current_oauth_index = load_start_indices()
    ...



load_dotenv()

KST = timezone(timedelta(hours=9))

def now_kst():
    return datetime.now(KST).strftime(
        "%Y-%m-%d %H:%M:%S"
    )

BOT_STATE_FILE = "bot_state.json"

def _pt_quota_date():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    except Exception:
        return (datetime.now(timezone.utc) - timedelta(hours=8)).strftime("%Y-%m-%d")

def next_quota_reset_kst():
    try:
        from zoneinfo import ZoneInfo
        nxt = (datetime.now(ZoneInfo("America/Los_Angeles")) + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0)
        return nxt.astimezone(KST)
    except Exception:
        return (datetime.now(timezone.utc) + timedelta(days=1)).replace(
            hour=8, minute=0, second=0, microsecond=0).astimezone(KST)

def _load_state():
    try:
        with open(BOT_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_state(**kw):
    s = _load_state()
    s.update(kw)
    s["pt_date"] = _pt_quota_date()
    try:
        with open(BOT_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("⚠️ bot_state 저장 실패:", e)


def get_active_auto_pins():
    """만료 안 지난 신곡 자동핀 video_id 목록. 만료된 건 정리해서 저장."""
    state = _load_state()
    pins = state.get("auto_pinned", {})
    if not pins:
        return []
    today = date.today()
    kept = {}
    for vid, added in pins.items():
        try:
            added_date = date.fromisoformat(added)
        except (ValueError, TypeError):
            continue
        if (today - added_date).days < AUTO_PIN_NEW_SONG_DAYS:
            kept[vid] = added
    if kept != pins:                      # 만료된 게 있으면 정리 후 저장
        _save_state(auto_pinned=kept)
    return list(kept.keys())

def add_auto_pin(video_id):
    """신곡 감지 시 호출. 이미 등록돼 있으면 날짜 유지(무시)."""
    if AUTO_PIN_NEW_SONG_DAYS <= 0:
        return
    state = _load_state()
    pins = state.get("auto_pinned", {})
    if video_id in pins:
        return
    pins[video_id] = date.today().isoformat()
    _save_state(auto_pinned=pins)

def _views_n_days_ago(history, days=7):
    """history에서 days일 전 시점에 가장 가까운(그 이전) 조회수. 7일치 안 되면 가장 오래된 값."""
    if not history:
        return None
    cutoff = datetime.strptime(str(now_kst()), "%Y-%m-%d %H:%M:%S") - timedelta(days=days)
    older = [h for h in history
             if datetime.strptime(h["updated"], "%Y-%m-%d %H:%M:%S") <= cutoff]
    if older:
        return older[-1]["views"]      # cutoff 이전 중 가장 최근
    return history[0]["views"]          # 아직 7일 안 됐으면 가장 오래된 값


def maybe_send_weekly_recap(data):
    """일요일 21시 이후 첫 실행에 지난 7일 결산 1회 전송 (bot_state 중복 방지)."""
    now = datetime.strptime(str(now_kst()), "%Y-%m-%d %H:%M:%S")
    if now.weekday() != 6 or now.hour < 21:   # 월=0 … 일=6
        return
    today = now_kst()[:10]
    if _load_state().get("last_weekly_recap") == today:
        return

    rows = []
    for vid, info in data.items():
        if vid.startswith("_") or not isinstance(info, dict):
            continue
        past = _views_n_days_ago(info.get("history", []), 7)
        if past is None:
            continue
        now_v = info.get("views", 0)
        delta = now_v - past
        if delta <= 0:
            continue
        rows.append({
            "title": info.get("title", vid),
            "artist": ", ".join(info.get("artists", [])),
            "delta": delta, "now": now_v, "past": past,
            "pct": (delta / past * 100) if past > 0 else 0,
        })

    if rows:
        rows.sort(key=lambda r: r["delta"], reverse=True)

        milestones = []
        for r in rows:
            start = ((r["past"] // 50000) + 1) * 50000
            for m in range(start, r["now"] + 1, 50000):
                label = f"{m // 10000}만" if m % 10000 == 0 else f"{m:,}"
                milestones.append((r["title"], m, label))
        milestones.sort(key=lambda x: x[1], reverse=True)

        top = "\n".join(
            f"{i}. {r['title']} — +{r['delta']:,}회 (+{r['pct']:.1f}%)  ({r['artist']})"
            for i, r in enumerate(rows[:5], 1)
        )
        rate_rows = sorted([r for r in rows if r["past"] >= 10000],
                           key=lambda r: r["pct"], reverse=True)
        rate_top = "\n".join(
            f"{i}. {r['title']} — +{r['pct']:.1f}% (+{r['delta']:,}회)  ({r['artist']})"
            for i, r in enumerate(rate_rows[:3], 1)
        )
        total = sum(r["delta"] for r in rows)

        msg = (
            "📊 주간 결산\n\n"
            f"🕒 {today} 기준 · 지난 7일\n\n"
            f"📈 최다 상승 5곡\n{top}\n\n"
        )
        if rate_top:
            msg += f"🚀 급상승률 3곡\n{rate_top}\n\n"
        if milestones:
            ms = "\n".join(f"  · {t} — {label} 돌파" for t, m, label in milestones[:8])
            msg += f"🎉 이번 주 새 기록\n{ms}\n\n"
        msg += f"🔥 전체 합산 상승: +{total:,}회"
        send_telegram(msg)

    _save_state(last_weekly_recap=today)   # 대상 없어도 오늘 체크 완료 기록




def load_start_indices():
    s = _load_state()
    if s.get("pt_date") == _pt_quota_date():
        ki = max(0, min(int(s.get("key_index", 0)), len(YOUTUBE_API_KEYS) - 1))
        oi = max(0, min(int(s.get("oauth_index", 0)), len(YOUTUBE_OAUTH) - 1))
        return ki, oi
    return 0, 0

def _advance_key():
    global _current_key_index
    if _current_key_index + 1 < len(YOUTUBE_API_KEYS):
        _current_key_index += 1
        _save_state(key_index=_current_key_index)
        return True
    return False

def _advance_oauth():
    global _current_oauth_index
    if _current_oauth_index + 1 < len(YOUTUBE_OAUTH):
        _current_oauth_index += 1
        _save_state(oauth_index=_current_oauth_index)
        return True
    return False

def next_quota_reset_kst():
    """YouTube 할당량은 태평양 자정에 리셋됨. 다음 리셋 시각을 KST로 반환."""
    try:
        from zoneinfo import ZoneInfo
        now_pt = datetime.now(ZoneInfo("America/Los_Angeles"))
        nxt = (now_pt + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        return nxt.astimezone(KST)
    except Exception:
        # 폴백: PT를 UTC-8로 가정 (자정 PST = 08:00 UTC = 17:00 KST)
        now_utc = datetime.now(timezone.utc)
        nxt = (now_utc + timedelta(days=1)).replace(
            hour=8, minute=0, second=0, microsecond=0
        )
        return nxt.astimezone(KST)


from config import (
    VIEW_STEP,
    MILESTONES,
    MILESTONE_TEMPLATE,
    EXCLUDE_KEYWORDS,
    STELLIVE_EXCLUDED_ARTIST_ALIASES,
    INITIAL_SETUP,
    UNITS,
    MAX_GROWTH_PLAYLIST_VIDEOS,
    GROWTH_PLAYLIST_ID,
    SYNC_GROWTH_PLAYLIST,
    GROWTH_PLAYLIST_REMOVE_MISSING,
    MAX_PLAYLIST_OPS_PER_RUN,
    EXCLUDED_VIDEO_IDS,
    GROWTH_PLAYLIST_PINNED,
    SHOW_SONG_TYPE_BADGE,
    USE_ARTIST_COLOR,
    SPECIAL_MILESTONES,
    PLAYLIST_ROTATE_COUNT,
    PLAYLIST_ROTATE_HOURS,
    SPECIAL_CARD_ENABLED,
    AUTO_PIN_NEW_SONG_DAYS,
    GROWTH_BOOST,
    BOOST_DEFAULT_DAYS,
    DDAY_THRESHOLD_DAYS,
    DDAY_ALERT_HOUR,
    IMMINENT_HOURS,
    SPIKE_MULT,
    SPIKE_MIN_DAILY,
    DDAY_MAJOR_STEP,
    UNITS
)

from card import make_milestone_card



# ======================
# 환경 변수
# ======================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# ===== API 키 (읽기) — 소진 시 자동 전환 =====
YOUTUBE_API_KEYS = [
    k.strip() for k in (
        os.environ.get("YOUTUBE_API_KEY", ""),
        os.environ.get("YOUTUBE_API_KEY_2", ""),
        os.environ.get("YOUTUBE_API_KEY_3", ""),
    ) if k.strip()
]
if not YOUTUBE_API_KEYS:
    raise RuntimeError("YOUTUBE_API_KEY 환경변수가 없습니다.")
YOUTUBE_API_KEY = YOUTUBE_API_KEYS[0]   # 하위호환
_current_key_index = 0

def current_api_key():
    return YOUTUBE_API_KEYS[_current_key_index]

# ===== OAuth (쓰기) — 소진 시 자동 전환 =====
YOUTUBE_OAUTH = []
for _sfx in ("", "_2", "_3"):
    _cid = os.environ.get(f"YOUTUBE_CLIENT_ID{_sfx}")
    _csec = os.environ.get(f"YOUTUBE_CLIENT_SECRET{_sfx}")
    _rtok = os.environ.get(f"YOUTUBE_REFRESH_TOKEN{_sfx}")
    if _cid and _csec and _rtok:
        YOUTUBE_OAUTH.append({"client_id": _cid, "client_secret": _csec, "refresh_token": _rtok})
_current_oauth_index = 0


KEY_STATE_FILE = "key_state.json"

def _pt_quota_date():
    """태평양 기준 오늘 날짜 (할당량 리셋 경계)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d")
    except Exception:
        return (datetime.now(timezone.utc) - timedelta(hours=8)).strftime("%Y-%m-%d")

def load_start_key_index():
    """오늘(PT) 소진돼서 넘어간 키 번호를 불러옴. 날짜 바뀌면 0부터."""
    try:
        with open(KEY_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)
        if state.get("pt_date") == _pt_quota_date():
            idx = int(state.get("start_key_index", 0))
            return max(0, min(idx, len(YOUTUBE_API_KEYS) - 1))
    except Exception:
        pass
    return 0

def save_start_key_index(idx):
    try:
        with open(KEY_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump({"pt_date": _pt_quota_date(), "start_key_index": idx},
                      f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ key_state 저장 실패: {e}")

def maybe_send_dday_digest(data):
    """100만 단위 목표 임박 곡을 매일 1회 텔레그램으로 (bot_state 중복 방지)."""
    now = datetime.strptime(str(now_kst()), "%Y-%m-%d %H:%M:%S")
    if now.hour < DDAY_ALERT_HOUR:
        return
    today = now_kst()[:10]
    if _load_state().get("last_dday_date") == today:
        return

    rows = []
    for vid, info in data.items():
        if vid.startswith("_") or not isinstance(info, dict):
            continue
        speed = info.get("growth", {}).get("daily_avg", 0)
        if speed <= 0:
            continue
        views = info.get("views", 0)
        target = ((views // DDAY_MAJOR_STEP) + 1) * DDAY_MAJOR_STEP   # 다음 100만
        eta = (target - views) / speed
        if eta > DDAY_THRESHOLD_DAYS:
            continue
        rows.append({
            "title": info.get("title", vid),
            "artist": ", ".join(info.get("artists", [])),
            "target": target, "eta": eta, "speed": speed,
        })

    if rows:
        rows.sort(key=lambda r: r["eta"])
        lines = []
        for r in rows[:10]:
            tag = "오늘·내일" if r["eta"] < 1.5 else f"D-{round(r['eta'])}"
            lines.append(
                f"· {r['title']} — {r['target'] // 10000}만 {tag} "
                f"(하루 +{r['speed']:,.0f})  ({r['artist']})"
            )
        send_telegram("🔜 곧 달성 예정 (100만 단위)\n\n🕒 " + today + "\n\n" + "\n".join(lines))

    _save_state(last_dday_date=today)


def send_imminent_alerts(data):
    """다음 목표 임박 곡을 한 메시지로 모아 알림 (곡·목표별 1회)."""
    now = datetime.now(KST)
    alerted = dict(_load_state().get("imminent_alerted", {}))
    picks, changed = [], False
    for vid, info in data.items():
        if vid.startswith("_") or not isinstance(info, dict):
            continue
        g = info.get("growth", {})
        eta = g.get("eta_days")
        if eta is None or eta == float("inf") or eta * 24 > IMMINENT_HOURS:
            continue
        views = info.get("views", 0)
        target = views + g.get("remaining", 0)
        if alerted.get(vid) == target:      # 이 목표는 이미 알림 → skip
            continue
        picks.append((eta, vid, info, target))
        alerted[vid] = target
        changed = True

    if picks:
        picks.sort(key=lambda x: x[0])
        lines = []
        for eta, vid, info, target in picks:
            when = now + timedelta(days=eta)
            if when.date() == now.date():
                day = "오늘"
            elif when.date() == (now + timedelta(days=1)).date():
                day = "내일"
            else:
                day = when.strftime("%m/%d")
            tgt = f"{target // 10000}만" if target % 10000 == 0 else f"{target:,}"
            title = info.get("title", vid)
            artist = ", ".join(info.get("artists", []))
            lines.append(
                f"· {title} — {tgt} ({day} {when.hour}시경 예상)\n"
                f"  {artist}\n"
                f"  https://youtu.be/{vid}"
            )
        send_telegram("⚡ 곧 달성 예정\n\n" + "\n\n".join(lines))

    if changed:
        _save_state(imminent_alerted=alerted)


def send_spike_alerts(data):
    """최근 성장 속도가 평소보다 급등한 곡을 즉시 알림 (곡별 하루 1회)."""
    today = now_kst()[:10]
    fired = dict(_load_state().get("spike_fired", {}))   # {video_id: "YYYY-MM-DD"}
    changed = False
    for vid, info in data.items():
        if vid.startswith("_") or not isinstance(info, dict):
            continue
        g = info.get("growth", {})
        d1 = g.get("daily_1d", 0)
        base = g.get("daily_7d", 0) or g.get("daily_3d", 0)   # 7일 없으면 3일 기준
        if base <= 0 or d1 < SPIKE_MIN_DAILY or d1 < SPIKE_MULT * base:
            continue
        if fired.get(vid) == today:      # 오늘 이미 알림 → skip (하루 1회 쿨다운)
            continue
        title = info.get("title", vid)
        artist = ", ".join(info.get("artists", []))
        send_telegram(
            f"🚀 떡상 감지!\n\n"
            f"🎵 {title}  ({artist})\n"
            f"📈 최근 속도 평소의 {d1 / base:.1f}배\n"
            f"📊 하루 +{d1:,.0f}회 (현재 {info.get('views', 0):,}회)"
        )
        fired[vid] = today
        changed = True
    if changed:
        _save_state(spike_fired=fired)


# 아티스트 이름/별칭 → 유닛 역매핑 (모듈 로드 시 1회 구성)
_ARTIST_UNIT = {}
for _uname, _u in UNITS.items():
    for _mname, _m in _u.get("members", {}).items():
        _ARTIST_UNIT[_mname] = _uname
        for _alias in _m.get("aliases", []):
            _ARTIST_UNIT[_alias] = _uname


def resolve_unit(artists):
    """솔로/한유닛 → 그 유닛, 여러 유닛 → 콜라보, 스텔라이브 크레딧 → 스텔라이브."""
    found = set()
    for a in (artists or []):
        u = _ARTIST_UNIT.get(a)
        if u:
            found.add(u)
    if "스텔라이브" in found:          # 공식 그룹 곡
        return "스텔라이브"
    real = found - {"스텔라이브"}
    if len(real) == 1:
        return next(iter(real))       # 단일 유닛
    if len(real) >= 2:
        return "듀엣"               # 크로스유닛 콜라보
    return ""



# ======================
# 파일 저장
# ======================

DATA_FILE = "views.json"
TITLE_FILE = "titles.json"
SNAPSHOTS_FILE = "snapshots.json"

HISTORY_LIMIT = 30


def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2
        )


# ======================
# 텔레그램
# ======================

def send_telegram(message, reply_markup=None):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    response = requests.post(url, json=payload, timeout=10)

    print("===== Telegram 결과 =====")
    print(response.status_code)
    print(response.text)
    print("========================")


def send_telegram_photo(message, video_id, reply_markup=None):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendPhoto"
    )

    thumbnail = (
        f"https://img.youtube.com/vi/"
        f"{video_id}/maxresdefault.jpg"
    )

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "photo": thumbnail,
        "caption": message
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    response = requests.post(url, json=payload, timeout=10)

    print("===== Telegram Photo 결과 =====")
    print(response.status_code)
    print(response.text)
    print("==============================")

    return response.ok

def send_card_photo(image_path, caption, reply_markup=None):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendPhoto"
    )

    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)

    with open(image_path, "rb") as f:
        response = requests.post(
            url, data=data, files={"photo": f}, timeout=30
        )

    print("===== Telegram Card 결과 =====")
    print(response.status_code, response.text)
    return response.ok


def make_x_button(text):
    tweet_url = "https://twitter.com/intent/tweet?text=" + quote(text)
    return {
        "inline_keyboard": [[
            {"text": "X에 POST", "url": tweet_url}
        ]]
    }


def send_notification(message, video_id=None, card_info=None):
    markup = make_x_button(message)
    if video_id and card_info:
        try:
            milestone = card_info.get("milestone")
            if SPECIAL_CARD_ENABLED and milestone in SPECIAL_MILESTONES:
                card_path = make_special_card(
                    video_id, card_info["title"], card_info["artist"],
                    f"/tmp/card_{video_id}.jpg", milestone=milestone,
                )
            else:
                card_opts = card_info.get("card_opts")
                if isinstance(card_opts, dict) and card_opts.get("grand"):
                    card_opts = {k: v for k, v in card_opts.items()
                                 if k not in ("grand", "accent", "tint", "tagline")} or None
                card_path = make_milestone_card(
                    video_id, card_info["title"], card_info["artist"],
                    card_info["views_text"], f"/tmp/card_{video_id}.jpg",
                    song_type=card_info.get("song_type", ""),
                    card_opts=card_opts,
                )
            if send_card_photo(card_path, message, reply_markup=markup):
                return
        except Exception as e:
            print(f"⚠️ 카드 생성/전송 실패 → 기본 썸네일로 대체: {e}")
    if video_id and send_telegram_photo(message, video_id, reply_markup=markup):
        return
    send_telegram(message, reply_markup=markup)


def log_daily_snapshot(video_id, views):
    """하루 1개만 조회수 스냅샷 저장 (연말결산용, 절대 안 지움)."""
    today = now_kst()[:10]   # "2026-09-09"
    try:
        with open(SNAPSHOTS_FILE, encoding="utf-8") as f:
            snaps = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        snaps = {}
    day = snaps.setdefault(video_id, {})
    if today not in day:               # 그날 첫 기록만 (하루 1회만 파일 씀)
        day[today] = views
        with open(SNAPSHOTS_FILE, "w", encoding="utf-8") as f:
            json.dump(snaps, f, ensure_ascii=False)


def send_error(error):

    message = (
        "⚠️ YouTube Notify 오류 발생\n\n"
        f"🕒 시간: {now_kst()}\n\n"
        f"❌ 내용:\n{error}"
    )

    send_telegram(message)


def send_photo(photo, caption):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendPhoto"
    )

    requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": photo,
            "caption": caption
        },
        timeout=10
    )


def get_reached_milestones(views):

    reached = []

    step = views // VIEW_STEP

    for i in range(1, step + 1):
        reached.append(i * VIEW_STEP)

    for milestone in MILESTONES:
        if views >= milestone:
            reached.append(milestone)

    return list(set(reached))


# ======================
# YouTube API
# ======================

def youtube_get(url, params, description="YouTube API 요청", max_retries=4):
    global _current_key_index
    for attempt in range(max_retries + 1):
        req_params = {**params, "key": current_api_key()}
        try:
            response = requests.get(url, params=req_params, timeout=10)
        except RequestException as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(
                    f"⚠️ YouTube 네트워크 오류: {description} "
                    f"→ {wait}초 후 재시도 ({attempt + 1}/{max_retries})"
                )
                time.sleep(wait)
                continue

            message = (
                "⚠️ YouTube API 요청 실패\n\n"
                f"🕒 시간: {now_kst()}\n"
                f"📌 요청: {description}\n"
                f"❌ 내용: {e}\n\n"
                "🔁 자동 재시도를 모두 소진했습니다."
            )
            send_telegram(message)
            raise

        if response.status_code == 403:
            try:
                error_data = response.json()
                reasons = [
                    error.get("reason", "")
                    for error in error_data.get("error", {}).get("errors", [])
                ]
            except Exception:
                reasons = []

            if (
                any(reason in {"quotaExceeded", "dailyLimitExceeded"} for reason in reasons)
                or "quotaExceeded" in response.text
                or "dailyLimitExceeded" in response.text
            ):
                # 다음 키가 있으면 자동 전환 후 같은 요청 재시도
                if _current_key_index + 1 < len(YOUTUBE_API_KEYS):
                    old_no = _current_key_index + 1
                    _current_key_index += 1
                    save_start_key_index(_current_key_index)
                    new_no = _current_key_index + 1
                    if _advance_key():
                        continue
                reset_kst = next_quota_reset_kst()
                hours_left = (reset_kst - datetime.now(KST)).total_seconds() / 3600
                message = (
                    "🚨 YouTube API quota 초과\n\n"
                    f"🕒 시간: {now_kst()}\n"
                    f"📌 요청: {description}\n\n"
                    "⛔ 모든 읽기 키의 할당량이 소진되어 중단했습니다.\n"
                    f"🔄 예상 리셋: {reset_kst.strftime('%m/%d %H:%M')} KST "
                    f"(약 {hours_left:.0f}시간 뒤)"
                )
                print(message)
                send_telegram(message)
                raise QuotaExceededError("YouTube API quotaExceeded")



        if response.status_code in {409, 500, 502, 503, 504}:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(
                    f"⚠️ YouTube API 일시 오류 {response.status_code}: "
                    f"{description} → {wait}초 후 재시도 "
                    f"({attempt + 1}/{max_retries})"
                )
                time.sleep(wait)
                continue

            message = (
                "⚠️ YouTube API 일시 오류 반복\n\n"
                f"🕒 시간: {now_kst()}\n"
                f"📌 요청: {description}\n"
                f"❌ HTTP {response.status_code}\n\n"
                "🔁 자동 재시도를 모두 소진했습니다."
            )
            print(message)
            send_telegram(message)
            raise RuntimeError(
                f"YouTube API 일시 오류 {response.status_code}: {description}"
            )

        try:
            response.raise_for_status()
        except RequestException as e:
            raise RuntimeError(
                f"YouTube API 오류: HTTP {response.status_code}: {description}: {e}"
            ) from e

        return response.json()


def get_channel_id(handle):

    data = youtube_get(
        "https://www.googleapis.com/youtube/v3/channels",
        {
            "part": "id",
            "forHandle": handle.replace("@", ""),
            "key": YOUTUBE_API_KEY
        }
    )

    items = data.get("items")

    if not items:
        return None

    return items[0]["id"]


def sort_artists_by_config_order(artist_names):
    ordered_names = []
    for unit, unit_data in UNITS.items():
        for artist_name in unit_data["members"].keys():
            if artist_name in artist_names:
                ordered_names.append(artist_name)
    return ordered_names

def classify_song(title):
    """제목으로 종류 판별 → (오리지널|커버, 3D 여부)."""
    t = (title or "").lower()
    is_cover = any(k in t for k in ["cover", "커버", "COVER", "Cover"])
    is_3d = "3d" in t
    return ("커버" if is_cover else "오리지널"), is_3d



# =========================
# 음악 영상 제외 판단
# =========================

def is_excluded(title):

    title_lower = title.lower()

    for word in EXCLUDE_KEYWORDS:
        if word.lower() in title_lower:
            return True

    return False


# =========================
# 아티스트 설정 가져오기 (안전 처리 강화)
# =========================

def get_artist_info(artist_name):
    for unit, unit_data in UNITS.items():
        members = unit_data["members"]
        if artist_name in members:
            return members[artist_name]
    return {
        "channel": "", "display": artist_name, "keyword": "",
        "nickname": artist_name, "aliases": [artist_name],
        "color": "", "mark": ""
    }

def expand_artists(artist_list):
    result = []
    for name in artist_list:
        if name in UNITS:
            for member in UNITS[name]["members"].keys():
                if member not in result:
                    result.append(member)
        elif name not in result:
            result.append(name)
    return result

def collapse_artists(artist_list):
    remaining = list(artist_list)
    result = []
    for unit, unit_data in UNITS.items():
        member_names = list(unit_data["members"].keys())
        if len(member_names) < 2:
            continue
        if all(m in remaining for m in member_names):
            result.append(unit)
            remaining = [a for a in remaining if a not in member_names]
    result.extend(remaining)
    return result



def _is_hangul_char(ch):
    return bool(ch) and (
        "\uAC00" <= ch <= "\uD7A3"    # 완성형 한글 음절
        or "\u1100" <= ch <= "\u11FF"  # 한글 자모
        or "\u3130" <= ch <= "\u318F"  # 호환용 자모
    )


def alias_in_title(alias, title_lower):
    """
    제목 안에 별칭이 들어있는지 검사.
    '나나'가 '나나호시' 안에서 잘못 잡히는 걸 막으려고,
    3글자 이하 짧은 별칭은 앞뒤가 다른 한글 글자에 붙어 있으면
    (= 더 긴 단어의 일부면) 매칭으로 치지 않는다.
    """
    alias = (alias or "").strip().lower()
    if not alias:
        return False

    short_alias = len(alias) <= 3
    start = 0

    while True:
        idx = title_lower.find(alias, start)
        if idx == -1:
            return False

        if not short_alias:
            return True

        before = title_lower[idx - 1] if idx > 0 else ""
        after_pos = idx + len(alias)
        after = title_lower[after_pos] if after_pos < len(title_lower) else ""

        # 짧은 별칭이 한글 글자에 붙어 있으면 더 긴 이름의 일부로 보고 건너뜀
        if _is_hangul_char(before) or _is_hangul_char(after):
            start = idx + 1
            continue

        return True


def normalize_artists(artists):
    if not isinstance(artists, list):
        return []
    cleaned = [
        artist.strip()
        for artist in artists
        if isinstance(artist, str) and artist.strip()
    ]
    return list(dict.fromkeys(cleaned))

def resolve_artist_mark(artist_display, effective_artists):
    for name in [artist_display] + list(effective_artists):
        m = get_artist_info(name).get("mark")
        if m:
            return m
    return ""

def resolve_effective_artists(auto_artists, override):
    """
    사용자가 직접 지정한 override가 있으면 (적은 순서 그대로) 그걸 쓰고,
    없으면 자동 판별된 아티스트를 쓴다.
    """
    normalized_override = normalize_artists(override)
    if normalized_override:
        return normalized_override
    return auto_artists


def get_artists_from_title(title):
    title_lower = title.lower()
    matched_artists = []
    for unit, unit_data in UNITS.items():
        if unit == "스텔라이브":
            continue
        for artist_name, artist_info in unit_data["members"].items():
            aliases = [
                artist_name,
                artist_info.get("display", artist_name),
                artist_info.get("keyword", ""),
                artist_info.get("nickname", ""),
                *artist_info.get("aliases", [])
            ]
            if any(isinstance(a, str) and alias_in_title(a, title_lower) for a in aliases):
                matched_artists.append(artist_name)
    return sort_artists_by_config_order(list(dict.fromkeys(matched_artists)))



def is_excluded_stellive_video(title):
    title_lower = title.lower()

    excluded_aliases = list(STELLIVE_EXCLUDED_ARTIST_ALIASES)

    excluded_aliases.extend([
        "아이리 칸나",
        "아이리칸나",
        "Airi Kanna",
        "AiriKanna",
    ])

    return any(
        alias and alias.lower() in title_lower
        for alias in excluded_aliases
    )


def _boost_multiplier(video_id, artists):
    """오늘 기준 유효한 부스트 배율. 여러 개 겹치면 곱함. 기본 1.0."""
    today = now_kst()[:10]
    starts = _load_state().get("boost_starts", {})
    mult = 1.0
    for b in GROWTH_BOOST:
        btype, target = b.get("type"), b.get("target")
        hit = (btype == "song"   and target == video_id) or \
              (btype == "artist" and target in (artists or []))
        if not hit:
            continue
        until = str(b.get("until", "")).strip()
        if until:
            active = until >= today                          # 종료일 당일까지 유효
        else:
            start = starts.get(f"{btype}:{target}", today)   # 종료일 없으면 처음 본 날부터
            elapsed = (datetime.strptime(today, "%Y-%m-%d")
                       - datetime.strptime(start, "%Y-%m-%d")).days
            active = elapsed < BOOST_DEFAULT_DAYS             # 10일간
        if active:
            mult *= 1.0 + b.get("pct", 0) / 100.0
    return mult

def refresh_boost_starts():
    """until 없는 부스트의 시작일을 bot_state에 기록/정리 (실행당 1회)."""
    today = now_kst()[:10]
    starts = dict(_load_state().get("boost_starts", {}))
    current = {
        f"{b.get('type')}:{b.get('target')}"
        for b in GROWTH_BOOST
        if not str(b.get("until", "")).strip()    # 종료일 없는 것만 추적
    }
    changed = False
    for key in current:                            # 새로 등록된 건 오늘 stamp
        if key not in starts:
            starts[key] = today; changed = True
    for key in list(starts):                       # config에서 빠진 건 정리(재등록 시 새 10일)
        if key not in current:
            del starts[key]; changed = True
    if changed:
        _save_state(boost_starts=starts)


# =========================
# 플레이리스트
# =========================

def add_title_artists(video, title):

    for artist_name in get_artists_from_title(title):
        if artist_name not in video["artists"]:
            video["artists"].append(artist_name)

    video["artists"] = sort_artists_by_config_order(
        video["artists"]
    )

def extract_video_id(value):
    if not value:
        return ""
    match = re.search(
        r"(?:v=|youtu\.be/|/shorts/|/live/)([A-Za-z0-9_-]{11})",
        value
    )
    if match:
        return match.group(1)
    return value.strip()


def load_titles():
    try:
        with open(TITLE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return (data, True) if isinstance(data, dict) else ({}, False)
    except FileNotFoundError:
        return {}, True
    except Exception:
        return {}, False   # JSON 손상 → 덮어쓰기 금지 신호


def build_override_map(titles_raw):
    result = {}
    for key, value in titles_raw.items():
        vid = extract_video_id(key)
        if not vid:
            continue
        if isinstance(value, str):
            result[vid] = {"title": value.strip(), "artists": [], "card": None}
        elif isinstance(value, dict):
            t = value.get("title", "")
            a = value.get("artists", [])
            result[vid] = {
                "title": t.strip() if isinstance(t, str) else "",
                "artists": [x.strip() for x in a
                            if isinstance(x, str) and x.strip()]
                           if isinstance(a, list) else [],
                "card": value.get("card") if isinstance(value.get("card"), dict) else None
            }
    return result





def get_excluded_video_ids():
    result = set()
    for value in EXCLUDED_VIDEO_IDS:
        vid = extract_video_id(value)
        if vid:
            result.add(vid)
    return result


def get_playlist_videos():

    excluded_ids = get_excluded_video_ids()

    videos = {}

    checked_artists = []
    checked_units = []
    checked_playlists = 0
    error_playlists = 0

    # 1단계: 개인 재생목록
    for unit, artists in UNITS.items():

        if unit == "스텔라이브":
            continue

        if unit not in checked_units:
            checked_units.append(unit)

        for artist_name, info in artists["members"].items():

            if artist_name not in checked_artists:
                checked_artists.append(artist_name)

            for playlist_id in info["playlists"]:

                checked_playlists += 1

                try:
                    next_page = None

                    while True:
                        params = {
                            "part": "snippet",
                            "playlistId": playlist_id,
                            "maxResults": 50,
                            "key": YOUTUBE_API_KEY
                        }

                        if next_page:
                            params["pageToken"] = next_page

                        data = youtube_get(
                            "https://www.googleapis.com/youtube/v3/playlistItems",
                            params,
                            f"개인 재생목록 조회: {playlist_id}"
                        )

                        for item in data.get("items", []):
                            video_id = item["snippet"]["resourceId"]["videoId"]
                            title = item["snippet"]["title"]

                            if is_excluded(title):
                                continue

                            if video_id not in videos:
                                videos[video_id] = {
                                    "id": video_id,
                                    "title": title,
                                    "artists": [artist_name],
                                    "unit": unit,
                                    "is_stellive": False
                                }
                            else:
                                if artist_name not in videos[video_id]["artists"]:
                                    videos[video_id]["artists"].append(artist_name)

                            add_title_artists(videos[video_id], title)

                        next_page = data.get("nextPageToken")
                        if not next_page:
                            break
                except QuotaExceededError:
                    raise
                except Exception as e:
                    error_playlists += 1
                    send_telegram(
                        f"⚠️ 플레이리스트 오류\n\n"
                        f"🎤 아티스트: {artist_name}\n"
                        f"📁 Playlist ID: {playlist_id}\n\n"
                        f"❌ 내용:\n{e}"
                    )
                    continue


    # 2단계: 스텔라이브 본계 재생목록
    stellive_artists = UNITS.get("스텔라이브", {}).get("members", {})

    for artist_name, info in stellive_artists.items():

        if artist_name not in checked_artists:
            checked_artists.append(artist_name)

        if "스텔라이브" not in checked_units:
            checked_units.append("스텔라이브")

        for playlist_id in info["playlists"]:

            checked_playlists += 1

            try:
                next_page = None

                while True:
                    params = {
                        "part": "snippet",
                        "playlistId": playlist_id,
                        "maxResults": 50,
                        "key": YOUTUBE_API_KEY
                    }

                    if next_page:
                        params["pageToken"] = next_page

                    data = youtube_get(
                        "https://www.googleapis.com/youtube/v3/playlistItems",
                        params,
                        f"스텔라이브 재생목록 조회: {playlist_id}"
                    )

                    for item in data.get("items", []):
                        video_id = item["snippet"]["resourceId"]["videoId"]
                        title = item["snippet"]["title"]
                        owner_title = item["snippet"].get("videoOwnerChannelTitle", "")

                        if video_id in excluded_ids:
                            continue

                        if is_excluded(title):
                            continue

                        if video_id in videos:
                            add_title_artists(videos[video_id], title)
                            videos[video_id]["is_stellive"] = False
                            continue

                        if is_excluded_stellive_video(title) or is_excluded_stellive_video(owner_title):
                            continue

                        matched_artists = get_artists_from_title(title)

                        if matched_artists:
                            videos[video_id] = {
                                "id": video_id,
                                "title": title,
                                "artists": matched_artists,
                                "unit": "개인 판별",
                                "is_stellive": False
                            }
                        else:
                            videos[video_id] = {
                                "id": video_id,
                                "title": title,
                                "artists": ["스텔라이브"],
                                "unit": "스텔라이브",
                                "is_stellive": True
                            }

                    next_page = data.get("nextPageToken")
                    if not next_page:
                        break

            except QuotaExceededError:
                raise
            except Exception as e:
                error_playlists += 1
                send_telegram(
                    f"⚠️ 플레이리스트 오류\n\n"
                    f"🎤 아티스트: {artist_name}\n"
                    f"📁 Playlist ID: {playlist_id}\n\n"
                    f"❌ 내용:\n{e}"
                )
                continue

    # 각 아티스트에 직접 추가한 개별 영상 주입 (UNITS의 "videos")
    for unit, artists in UNITS.items():
        for artist_name, info in artists["members"].items():
            for raw_video in info.get("videos", []):
                manual_id = extract_video_id(raw_video)
                if not manual_id:
                    continue

                if manual_id in videos:
                    if artist_name not in videos[manual_id]["artists"]:
                        videos[manual_id]["artists"].append(artist_name)
                else:
                    videos[manual_id] = {
                        "id": manual_id,
                        "title": "",
                        "artists": [artist_name],
                        "unit": unit,
                        "is_stellive": False,
                    }



    videos = list(videos.values())

    print("===== Playlist 음악 영상 =====")
    for video in videos:
        print(f"[{', '.join(video['artists'])}] {video['title']}")
    print("총", len(videos), "개")
    print("============================")
    print(f"👥 확인 아티스트: {len(checked_artists)}명")
    print(f"📁 확인 플레이리스트: {checked_playlists}개")
    print(f"⚠️ 오류 플레이리스트: {error_playlists}개")

    return videos, checked_playlists, checked_units, checked_artists


# =========================
# 조회수 가져오기
# =========================

def get_view_counts(video_ids):

    result = {}

    for start in range(0, len(video_ids), 50):

        chunk = video_ids[start:start + 50]

        data = youtube_get(
            "https://www.googleapis.com/youtube/v3/videos",
            {
                "part": "snippet,statistics",
                "id": ",".join(chunk),
                "key": YOUTUBE_API_KEY
            }
        )

        for item in data.get("items", []):
            video_id = item["id"]
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})

            thumbnails = snippet.get("thumbnails", {})

            thumbnail = (
                thumbnails.get("high")
                or thumbnails.get("medium")
                or thumbnails.get("default")
                or {}
            ).get("url", "")

            result[video_id] = {
                "views": int(statistics.get("viewCount", 0)),
                "title": snippet.get("title", ""),
                "thumb": thumbnail,
                "published": snippet.get("publishedAt", "")
            }

    return result


# ======================
# 조회수 성장 분석
# ======================

def get_growth_stats(history, views):

    now = datetime.now(KST)

    def get_views_at(days):
        target = now - timedelta(days=days)
        candidates = []

        for item in history:
            try:
                updated = datetime.strptime(
                    item["updated"],
                    "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=KST)

                if updated <= target:
                    candidates.append((updated, item["views"]))

            except Exception:
                continue

        if not candidates:
            return None

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    views_1d = get_views_at(1)
    views_3d = get_views_at(3)
    views_7d = get_views_at(7)

    def daily_speed(old_views, days):
        if old_views is None:
            return 0
        increase = views - old_views
        if increase <= 0:
            return 0
        return increase / days

    daily_1d = daily_speed(views_1d, 1)
    daily_3d = daily_speed(views_3d, 3)
    daily_7d = daily_speed(views_7d, 7)

    speeds = [speed for speed in [daily_1d, daily_3d, daily_7d] if speed > 0]

    if speeds:
        daily_avg = (
            daily_1d * 0.50
            + daily_3d * 0.30
            + daily_7d * 0.20
        )
    else:
        daily_avg = 0

    next_target = ((views // VIEW_STEP) + 1) * VIEW_STEP
    remaining = next_target - views

    if daily_avg > 0:
        eta_days = remaining / daily_avg
    else:
        eta_days = float("inf")

    if daily_7d > 0:
        acceleration = daily_1d / daily_7d
    else:
        acceleration = 1.0

    return {
        "daily_1d": daily_1d,
        "daily_3d": daily_3d,
        "daily_7d": daily_7d,
        "daily_avg": daily_avg,
        "next_target": next_target,
        "remaining": remaining,
        "eta_days": eta_days,
        "acceleration": acceleration
    }


def calculate_growth_score(views, growth):
    daily_1d = growth["daily_1d"]
    daily_3d = growth["daily_3d"]
    daily_7d = growth["daily_7d"]
    acceleration = growth["acceleration"]
    remaining = growth["remaining"]

    speed = daily_1d * 0.5 + daily_3d * 0.3 + daily_7d * 0.2
    if speed <= 0:
        return 0

    # ① 상대 성장률: 조회수 대비 얼마나 빠른가 (작은 곡일수록 유리)
    relative = speed / max(1, views ** 0.7) # 0.6 올리면 묻힌 곡 더 강하게 나옴
    relative_score = min(100, relative * 65) # 60 올리면 묻힌 곡 더 강하게 나옴

    # ② 절대 속도 (유명곡도 조금 반영, 가중치 낮음)
    speed_score = min(100, speed / 1500)

    # ③ 다음 목표 근접도
    progress = max(0, min(1, 1 - (remaining / VIEW_STEP)))
    distance_score = (progress ** 2) * 100

    # ④ 저평가 보너스 (조회수 낮은데 성장 중)
    if views < 100000:
        underdog = 17                   # 15 올리면 묻힌 곡 더 강하게 나옴
    elif views < 300000:
        underdog = 9                    # 8 올리면 묻힌 곡 더 강하게 나옴
    else:
        underdog = 0

    # ⑤ 가속 보너스
    if acceleration > 1.2:
        acc = 8
    elif acceleration < 0.7:
        acc = -8
    else:
        acc = 0

    score = (
        relative_score * 0.45      # 상대 성장 최우선
        + distance_score * 0.20
        + speed_score * 0.15
        + underdog
        + acc
    )
    return round(max(0, min(100, score)), 2)


# ======================
# 알림용 정보 생성
# ======================

def get_notification_artist_info(artist_names):


    artist_infos = [
        get_artist_info(artist_name)
        for artist_name in artist_names
    ]

    return {
        "keyword": " ".join(
            info.get("keyword", "") for info in artist_infos if info.get("keyword")
        ),
        "nickname": " ".join(
            info.get("nickname", "") for info in artist_infos if info.get("nickname")
        )
    }


# ======================
# 알림 계산
# ======================

def check_milestone(
    old_views, views, title, url, notified,
    artist_info, video_id, artist_display=""
):

    alerts = []
    new_notified = []

    keywords = artist_info.get("keyword", "")
    nicknames = artist_info.get("nickname", "")

    old_step = old_views // VIEW_STEP
    new_step = views // VIEW_STEP

    if new_step > old_step:
        for i in range(old_step + 1, new_step + 1):
            count = i * VIEW_STEP
            if count in MILESTONES:
                continue
            if count not in notified:
                views_text = f"{count / 10000:g}만"
                alerts.append({
                    "message": MILESTONE_TEMPLATE.format(
                        keyword=keywords, nickname=nicknames,
                        title=title, views_text=views_text, url=url
                    ),
                    "video_id": video_id,
                    "title": title,
                    "artist": artist_display,
                    "views_text": views_text,
                    "views_count": views,
                    "milestone": count
                })
                new_notified.append(count)

    for milestone in set(MILESTONES):
        if old_views < milestone <= views and milestone not in notified:
            views_text = f"{milestone / 10000:g}만"
            alerts.append({
                "message": MILESTONE_TEMPLATE.format(
                    keyword=keywords, nickname=nicknames,
                    title=title, views_text=views_text, url=url
                ),
                "video_id": video_id,
                "title": title,
                "artist": artist_display,
                "views_text": views_text,
                "views_count": views,
                "milestone": milestone
            })
        if old_views < milestone <= views:
            new_notified.append(milestone)

    return alerts, new_notified


# ======================
# 성장 가능성 높은 영상 선정
# ======================

def get_top_growth_videos(data, limit=None):
    if limit is None:
        limit = MAX_GROWTH_PLAYLIST_VIDEOS

    candidates = []
    for video_id, info in data.items():
        if video_id.startswith("_") or not isinstance(info, dict):
            continue
        if "growth" not in info:
            continue

        override = normalize_artists(info.get("artists_override"))
        if override:
            artists = override
        else:
            raw = info.get("artists", [])
            raw = raw if isinstance(raw, list) else []
            artists = sort_artists_by_config_order(list(dict.fromkeys(raw)))

        candidates.append({
            "video_id": video_id,
            "title": info.get("title", ""),
            "artists": artists,
            "unit": info.get("unit", ""),
            "views": info.get("views", 0),
            "score": info.get("growth_score", 0),
            "eta_days": info["growth"].get("eta_days")
        })

    # 점수 5점 버킷 정렬 → 미세 출렁임으로 코어가 매시간 뒤집히는 것 방지.
    # 같은 버킷에선 조회수 낮은(묻힌) 곡 우선.
    candidates.sort(key=lambda x: (round(x["score"] / 5), -x["views"]), reverse=True)

    rotate_n = min(PLAYLIST_ROTATE_COUNT, limit)
    core_n = limit - rotate_n
    core = candidates[:core_n]                          # 상위 = 고정(안정)

    # 회전 풀: 코어 바로 아래 구간의 '점수 있는' 곡들 (묻힌 곡)     # 120 -> 240으로 늘리면 묻힌 곡 더 잘 잡힘
    pool = [c for c in candidates[core_n:core_n + 150] if c["score"] > 0]

    # 회전: 풀을 '하루 단위'로 한 번만 섞어 순서 고정 → 창(window)을 시간마다 뒤로 밀며 꺼냄.
    # 한 번 빠진 곡은 풀을 한 바퀴 돌기 전엔 다시 안 나옴 → 삭제→즉시 재추가(flip-flop) 방지.
    now = datetime.now(KST)
    if pool and rotate_n > 0:
        day_seed = now.timetuple().tm_yday
        random.Random(day_seed).shuffle(pool)              # 그날 순서 고정
        block = (now.timetuple().tm_yday * 24 + now.hour) // max(1, PLAYLIST_ROTATE_HOURS)
        offset = (block * rotate_n) % len(pool)            # 시간마다 rotate_n칸씩 전진
        take = min(rotate_n, len(pool))
        rotating = [pool[(offset + i) % len(pool)] for i in range(take)]
    else:
        rotating = []

    return (core + rotating)[:limit]




def detect_song_type(raw_title):
    t = (raw_title or "").lower()
    for kw in ["cover", "커버", "歌ってみた", "カバー", "カヴァー"]:
        if kw in t:
            return "COVER"
    return "ORIGINAL"

def resolve_artist_color(artist_display, effective_artists):
    if not USE_ARTIST_COLOR:
        return None
    for name in [artist_display] + list(effective_artists):
        c = get_artist_info(name).get("color")
        if c:
            return c
    return None



def clean_song_title(title, artist_names=None):

    cleaned = title.strip()

    cleaned = re.sub(
        r"^\s*(?:\[?\s*)4k(?:\s*[-_]?\s*(?:60(?:fps)?|120(?:fps)?))?(?:\s*\]?\s*)[|:/_-]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    if re.search(r"\bplaylist\b", cleaned, flags=re.IGNORECASE):
        return cleaned

    names = ["스텔라이브", "StelLive"]

    for artist_name in artist_names or []:
        artist_info = get_artist_info(artist_name)

        names.extend([
            artist_name,
            artist_info.get("display", artist_name),
            *artist_info.get("aliases", [])
        ])

    names = sorted(
        {name for name in names if name},
        key=len,
        reverse=True
    )

    name_pattern = "|".join(
        re.escape(name)
        for name in names
    )

    if name_pattern:
        cleaned = re.sub(
            rf"^\s*[\[［(（]\s*(?:{name_pattern})\s*[\]］)）]\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

    cleaned = re.split(
        r"\s*(?:cover|歌ってみた|カバー)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()

    if name_pattern:
        cleaned = re.split(
            rf"\s*(?:/|ㅣ|-)\s*.*?(?:{name_pattern}).*$",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0].strip()

    cleaned = re.sub(
        r"\s*[\[［(（][^\]］)）]*[\]］)）]\s*$",
        "",
        cleaned
    ).strip()

    cleaned = re.sub(
        r"\s*[\[［][^\]］]*$",
        "",
        cleaned
    ).strip()

    return cleaned.strip(
        " \t-'\"'‘’“”「」『』[]［］()（）"
    )


# ======================
# YouTube 플레이리스트 쓰기 (OAuth)
# ======================

YOUTUBE_PLAYLIST_ITEMS_URL = "https://www.googleapis.com/youtube/v3/playlistItems"


def get_youtube_access_token():
    creds = YOUTUBE_OAUTH[_current_oauth_index]
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
        },
        timeout=10,
    )
    if not resp.ok:
        # Google의 사유만 남긴다. 자격증명 값은 절대 로그에 출력하지 않는다.
        try:
            detail = resp.json()
        except ValueError:
            detail = {}
        code = detail.get("error", "unknown_error")
        description = detail.get("error_description", "")
        raise RuntimeError(
            "OAuth 토큰 갱신 실패: "
            f"{code}" + (f" — {description}" if description else "")
        )
    return resp.json()["access_token"]



def fetch_playlist_items(access_token, playlist_id):
    """대상 플리의 현재 아이템들을 순서대로 가져온다."""
    headers = {"Authorization": f"Bearer {access_token}"}
    items = []
    next_page = None

    while True:
        params = {
            "part": "snippet",
            "playlistId": playlist_id,
            "maxResults": 50,
        }
        if next_page:
            params["pageToken"] = next_page

        response = requests.get(
            YOUTUBE_PLAYLIST_ITEMS_URL,
            headers=headers,
            params=params,
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            resource = snippet.get("resourceId", {})
            items.append({
                "playlist_item_id": item.get("id"),
                "video_id": resource.get("videoId"),
                "position": snippet.get("position"),
            })

        next_page = data.get("nextPageToken")
        if not next_page:
            break

    return items


def playlist_insert(access_token, playlist_id, video_id, position=None):
    headers = {"Authorization": f"Bearer {access_token}"}
    snippet = {
        "playlistId": playlist_id,
        "resourceId": {
            "kind": "youtube#video",
            "videoId": video_id,
        },
    }
    if position is not None:
        snippet["position"] = position

    response = requests.post(
        YOUTUBE_PLAYLIST_ITEMS_URL,
        headers=headers,
        params={"part": "snippet"},
        json={"snippet": snippet},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def playlist_delete(access_token, playlist_item_id):
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.delete(
        YOUTUBE_PLAYLIST_ITEMS_URL,
        headers=headers,
        params={"id": playlist_item_id},
        timeout=10,
    )
    if response.status_code not in (200, 204):
        response.raise_for_status()


def arrange_for_variety(videos):
    """
    점수순으로 정렬된 목록을 받아, 같은 아티스트가 연달아 나오지 않게
    최대한 섞어서 재배치한다. (점수 우선순위는 최대한 유지)
    """
    def primary(video):
        artists = video.get("artists") or []
        return artists[0] if artists else ""

    remaining = list(videos)
    arranged = []
    last_artist = None

    while remaining:
        pick_index = None
        for index, video in enumerate(remaining):
            if primary(video) != last_artist:
                pick_index = index
                break

        # 남은 게 전부 직전과 같은 아티스트면 그냥 점수 높은 것부터
        if pick_index is None:
            pick_index = 0

        chosen = remaining.pop(pick_index)
        arranged.append(chosen)
        last_artist = primary(chosen)

    return arranged




def _is_quota_error(error):
    response = getattr(error, "response", None)
    if response is None:
        return False
    if response.status_code != 403:
        return False
    text = response.text or ""
    return "quotaExceeded" in text or "dailyLimitExceeded" in text


def sync_growth_playlist(top_videos, title_map=None):
    title_map = title_map or {}
    if not SYNC_GROWTH_PLAYLIST:
        return  # 기능을 꺼둔 경우엔 조용히 넘어감

    if not YOUTUBE_OAUTH:
        send_telegram(
            "⚠️ 성장 플리 동기화 건너뜀\n\n"
            f"🕒 {now_kst()}\n"
            "❌ OAuth 자격증명(CLIENT_ID/SECRET/REFRESH_TOKEN)이 없습니다."
        )
        return

    if not GROWTH_PLAYLIST_ID:
        send_telegram(
            "⚠️ 성장 플리 동기화 건너뜀\n\n"
            f"🕒 {now_kst()}\n"
            "❌ GROWTH_PLAYLIST_ID가 설정되지 않았습니다."
        )
        return

    try:
        access_token = get_youtube_access_token()

        arranged = arrange_for_variety(top_videos)
        desired_ids = [v["video_id"] for v in arranged if v.get("video_id")]

        # 개인 고정 선곡 — 맨 앞에 항상 포함 (중복 제거)
        pinned = []
        for raw in GROWTH_PLAYLIST_PINNED:
            vid = extract_video_id(raw)
            if vid and vid not in pinned:
                pinned.append(vid)

        # 신곡 자동핀 (10일 한정) — 수동 고정곡 다음에 항상 포함
        for vid in get_active_auto_pins():
            if vid and vid not in pinned:
                pinned.append(vid)

        desired_ids = pinned + [vid for vid in desired_ids if vid not in pinned]

        desired_set = set(desired_ids)


        # 현재 플리 목록 읽기 (쿼터 소진 시 OAuth 프로젝트 전환)
        while True:
            try:
                current_items = fetch_playlist_items(access_token, GROWTH_PLAYLIST_ID)
                break
            except Exception as e:
                if _is_quota_error(e) and _advance_oauth():
                    access_token = get_youtube_access_token()
                    continue
                raise
        current_set = {
            it["video_id"] for it in current_items if it.get("video_id")
        }

        removed = 0
        added = 0
        ops = 0
        quota_hit = False
        added_titles = []       
        removed_titles = []

        # ── 삭제 ──
        if GROWTH_PLAYLIST_REMOVE_MISSING:
            for item in current_items:
                if item.get("video_id") in desired_set:
                    continue
                if ops >= MAX_PLAYLIST_OPS_PER_RUN:
                    break
                while True:
                    try:
                        playlist_delete(access_token, item["playlist_item_id"])
                        removed += 1; ops += 1
                        vid = item.get("video_id")
                        removed_titles.append(f"{title_map.get(vid, vid)}  ({vid})")
                        break
                    except Exception as e:
                        if _is_quota_error(e):
                            if _advance_oauth():
                                access_token = get_youtube_access_token()
                                continue
                            quota_hit = True
                            break
                        print(f"⚠️ 플리 삭제 실패 {item.get('video_id')}: {e}")
                        break
                if quota_hit:
                    break

        # ── 추가 ──
        if not quota_hit:
            for target_position, video_id in enumerate(desired_ids):
                if video_id in current_set:
                    continue
                if ops >= MAX_PLAYLIST_OPS_PER_RUN:
                    break
                while True:
                    try:
                        playlist_insert(access_token, GROWTH_PLAYLIST_ID, video_id, position=target_position)
                        added += 1; ops += 1
                        added_titles.append(f"{title_map.get(video_id, video_id)}  ({video_id})")
                        break
                    except Exception as e:
                        if _is_quota_error(e):
                            if _advance_oauth():
                                access_token = get_youtube_access_token()
                                continue
                            quota_hit = True
                            break
                        print(f"⚠️ 플리 추가 실패 {video_id}: {e}")
                        break
                if quota_hit:
                    break


        still_to_remove = 0
        if GROWTH_PLAYLIST_REMOVE_MISSING:
            still_to_remove = sum(
                1 for it in current_items
                if it.get("video_id") not in desired_set
            ) - removed
        still_to_add = sum(1 for vid in desired_ids if vid not in current_set) - added
        leftover = max(0, still_to_remove) + max(0, still_to_add)

        print(
            f"🎶 플리 동기화 | 추가 {added} · 삭제 {removed} · "
            f"목표 {len(desired_ids)}곡"
        )

        if quota_hit:
            note = "\n\n⚠️ 오늘 API 쿼터 소진 — 남은 정리는 리셋 후 이어감."
        elif leftover > 0:
            note = (
                f"\n\n⏳ 변경 상한({MAX_PLAYLIST_OPS_PER_RUN})까지만 처리 (고정곡·코어 우선) "
                f"\n\n남은 {leftover}곡은 다음 실행 때 그 시점 기준으로 재정리"
            )

        elif added == 0 and removed == 0:
            note = "\n\n✅ 변경 없음 (플리가 이미 최신 상태)"
        else:
            note = ""


        # 변경이 없어도 항상 상태 알림 전송
        def _fmt(titles, cap=15): # 15곡까지만 보이고 있는 중
            if not titles:
                return ""
            body = "\n".join(f"  · {t}" for t in titles[:cap])
            if len(titles) > cap:
                body += f"\n  …외 {len(titles) - cap}곡"
            return "\n" + body

        send_telegram(
            "🎶 성장 플리 자동 갱신\n\n"
            f"🕒 {now_kst()}\n"
            f"➕ 추가: {added}곡{_fmt(added_titles)}\n\n"
            f"➖ 삭제: {removed}곡{_fmt(removed_titles)}\n\n"
            f"📼 목표: {len(desired_ids)}곡\n"
            f"🔑 읽기 프로젝트: {_current_key_index + 1}번 · 쓰기 프로젝트: {_current_oauth_index + 1}번\n"
            f"{note}"
        )


    except Exception as e:
        print(f"⚠️ 성장 플리 동기화 중 오류: {e}")
        if _is_quota_error(e):
            send_telegram(
                "⏳ 성장 플리 동기화 보류\n\n"
                f"🕒 {now_kst()}\n"
                f"❌ 모든 프로젝트 쿼터 소진 — {next_quota_reset_kst()} 리셋 후 재개."
            )
        else:
            send_telegram(
                "⚠️ 성장 플리 동기화 실패\n\n"
                f"🕒 {now_kst()}\n"
                f"❌ {e}"
            )






# ======================
# 실행
# ======================

def main():
    global _current_key_index, _current_oauth_index
    # 이전 실행에서 쿼터 때문에 넘긴 API/OAuth 프로젝트부터 다시 시작한다.
    _current_key_index, _current_oauth_index = load_start_indices()

    refresh_boost_starts()

    checked_playlists = 0
    error_playlists = 0
    new_videos = 0

    data = load_data()

    titles_raw, titles_ok = load_titles()
    overrides = build_override_map(titles_raw)
    titles_dirty = False

    # 데이터가 비어있으면(초기화/손상 등) 이번 실행은 조용히 기준선만 재생성
    # → 모든 영상에 "새 영상" 알림이 도배되는 것 방지
    real_entries = [vid for vid in data if not vid.startswith("_")]
    baseline_mode = len(real_entries) == 0
    if baseline_mode:
        print("⚠️ 데이터 비어있음 — 기준선 재생성 모드 (알림 생략)")


    # 제외 목록 영상은 기존 데이터에서도 삭제
    for excluded_id in get_excluded_video_ids():
        data.pop(excluded_id, None)


    checked_videos = 0

    videos, checked_playlists, checked_units, checked_artists = get_playlist_videos()

    video_ids = [video["id"] for video in videos]

    view_data = get_view_counts(video_ids)

    for video in videos:

        checked_videos += 1

        video_id = video["id"]

        info = view_data.get(video_id)

        if info is None:
            print(f"⚠️ YouTube API에서 영상을 찾을 수 없음: {video_id}")
            continue

        views = info["views"]
        title = info["title"]

        auto_artists = video.get("artists", [])

        if not auto_artists:
            auto_artists = ["스텔라이브"]

        stored_entry = data.get(video_id, {})

        # 내가 직접 고친 아티스트(artists_override)가 있으면 그걸 우선 사용
        override = overrides.get(video_id)

        if override and override["artists"]:
            effective_artists = expand_artists(override["artists"])
        else:
            effective_artists = auto_artists

        stored_title = stored_entry.get("title")

        if override and override["title"]:
            display_title = override["title"]
        elif isinstance(stored_title, str) and stored_title.strip():
            display_title = stored_title.strip()
        else:
            display_title = clean_song_title(title, effective_artists)

        if titles_ok and video_id not in overrides:
            entry = {
                "title": display_title,
                "artists": collapse_artists(effective_artists),
                "orig": title,
                "url": f"https://youtu.be/{video_id}"
            }
            titles_raw[video_id] = entry
            overrides[video_id] = entry
            titles_dirty = True





        artist_info = get_notification_artist_info(effective_artists)

        # titles.json artists에 유닛명을 적었으면 알림 nickname을 유닛 호칭으로 교체
        if override and override["artists"]:
            unit_names = [n for n in override["artists"] if n in UNITS]
            if unit_names:
                artist_info = dict(artist_info)
                artist_info["nickname"] = UNITS[unit_names[0]].get("nickname", "얘들아 !!")



        url = f"https://www.youtube.com/watch?v={video_id}"

        is_new = video_id not in data

        if is_new:
            new_videos += 1

        if is_new and not INITIAL_SETUP and not baseline_mode:
            send_photo(
                info["thumb"],
                f"🆕 새로운 음악 영상 발견!\n\n"
                f"👤 {', '.join(effective_artists)}\n\n"
                f"🎵 {display_title}\n\n"
                f"📊 현재 조회수: {views:,}회\n\n"
                f"🔗 {url}"
            )
            add_auto_pin(extract_video_id(url))   # 신곡 → 성장 플리 10일 자동핀
            send_telegram(f"🎼 플리 자동 등록 (D-{AUTO_PIN_NEW_SONG_DAYS})")

        old_views = data.get(video_id, {}).get("views", views)

        video_data = data.get(video_id, {})

        history = video_data.get("history", [])

        if not isinstance(history, list):
            history = []

        growth = get_growth_stats(history, views)

        score = calculate_growth_score(views, growth)
        score *= _boost_multiplier(video_id, effective_artists)   # ← 추가: 부스트 배율 적용

        

        print(
            f"📊 {display_title}\n"
            f"   현재 조회수: {views:,}\n"
            f"   다음 목표까지: {growth['remaining']:,}회\n"
            f"   1일 속도: {growth['daily_1d']:,.0f}/일\n"
            f"   3일 속도: {growth['daily_3d']:,.0f}/일\n"
            f"   7일 속도: {growth['daily_7d']:,.0f}/일\n"
            f"   예상 속도: {growth['daily_avg']:,.0f}/일\n"
            f"   예상 달성: {growth['eta_days']:.2f}일\n"
            f"   성장 점수: {score}"
        )

        if is_new:
            messages = []
            new_notified = []
        else:
            messages, new_notified = check_milestone(
                old_views, views, display_title, url,
                data.get(video_id, {}).get("notified", []),
                artist_info, video_id,
                " · ".join(collapse_artists(effective_artists))
            )

        for alert in messages:
            song_card = {
                k: v for k, v in
                (((overrides.get(video_id) or {}).get("card")) or {}).items() if v
            }
            special = SPECIAL_MILESTONES.get(alert.get("milestone"), {})
            artist_color = resolve_artist_color(alert["artist"], effective_artists)

            opts = {}
            if artist_color:                 # 낮은 우선순위
                opts["accent"] = artist_color
                opts["tint"] = artist_color
            opts.update(special)             # 특별 마일스톤이 위
            opts.update(song_card)           # 곡별 지정이 최우선

            send_notification(
                alert["message"],
                alert["video_id"],
                card_info={
                    "title": alert["title"],
                    "artist": alert["artist"],
                    "views_text": alert["views_text"],
                    "song_type": detect_song_type(title) if SHOW_SONG_TYPE_BADGE else "",
                    "card_opts": opts
                }
            )



        if is_new and (INITIAL_SETUP or baseline_mode):
            notified = get_reached_milestones(views)
        else:
            notified = (
                data.get(video_id, {}).get("notified", []) + new_notified
            )

        history.append({
            "views": views,
            "updated": now_kst()
        })

        history = history[-300:] # 주간 결산용 요유 (-12일치)

        song_base, song_3d = classify_song(title)   # title = API 원제목 (커버/3D 키워드 살아있음)

        new_entry = {
            "title": display_title,
            "song_type": song_base,                 # 오리지널 / 커버
            "is_3d": song_3d,                         # 3D / 일반
            "artists": effective_artists,
            "unit": resolve_unit(effective_artists) or "기타",
            "published": info.get("published", "") or stored_entry.get("published", ""),
            "views": views,
            "history": history,
            "growth": {
                "remaining": growth["remaining"],
                "daily_1d": growth["daily_1d"],
                "daily_3d": growth["daily_3d"],
                "daily_7d": growth["daily_7d"],
                "daily_avg": growth["daily_avg"],
                "eta_days": growth["eta_days"]
            },
            "growth_score": score,
            "notified": sorted(set(notified)),
            "updated": str(now_kst())
        }
        

        # 내가 지정한 수정본은 다음 실행에서도 유지되도록 그대로 보존
        preserved_override = normalize_artists(
            stored_entry.get("artists_override")
        )
        if preserved_override:
            new_entry["artists_override"] = preserved_override

        data[video_id] = new_entry
        log_daily_snapshot(video_id, views)   # 연말결산용 일일 스냅샷



    status = (
        "✅ 이상 없음"
        if error_playlists == 0
        else f"⚠️ 오류 {error_playlists}개 있음"
    )

    send_telegram(
        f"✅ YouTube Notify 실행 완료\n\n"
        f"⏰ 실행 시간: {now_kst()}\n\n"
        f"🏠 확인 유닛: {', '.join(UNITS.keys())}\n"
        f"👥 확인 아티스트: {len(checked_artists)}명\n"
        f"📁 확인 플레이리스트: {checked_playlists}개\n"
        f"🎵 확인 영상: {checked_videos}개\n"
        f"🆕 새 영상: {new_videos}개\n\n"
        f"상태: {status}"
    )

    save_data(data)

    if titles_ok and titles_dirty:
        with open(TITLE_FILE, "w", encoding="utf-8") as f:
            json.dump(titles_raw, f, ensure_ascii=False, indent=2)
        print("📝 titles.json에 새 영상 자동 추가")

    if not titles_ok:
        send_telegram(
            "⚠️ titles.json 형식 오류로 읽지 못함\n"
            "오버라이드 무시 + 자동추가 건너뜀. 문법 확인 필요."
        )

    top_videos = get_top_growth_videos(
        data,
        limit=MAX_GROWTH_PLAYLIST_VIDEOS
    )

    data["_growth_playlist"] = {
        "updated": str(now_kst()),
        "videos": [
            {
                "video_id": video["video_id"],
                "title": video["title"],
                "artists": video["artists"],
                "views": video["views"],
                "score": video["score"],
                "eta_days": video["eta_days"]
            }
            for video in top_videos
        ]
    }

    print(
        f"===== 성장 가능성 TOP "
        f"{MAX_GROWTH_PLAYLIST_VIDEOS} ====="
    )

    for rank, video in enumerate(top_videos, start=1):
        print(
            f"{rank}. "
            f"[{video['score']}점] "
            f"[{', '.join(video['artists'])}] "
            f"{video['title']} "
            f"({video['views']:,}회)"
        )

    print("==============================")

    save_data(data)

    title_map = {
        vid: (info.get("title") or vid)
        for vid, info in data.items()
        if isinstance(info, dict)
    }
    
    sync_growth_playlist(top_videos, title_map)

    maybe_send_weekly_recap(data)   # 주간 결산 (일요일)
    maybe_send_dday_digest(data)    # 하루 결산 (매일 21시) ← 유지
    send_imminent_alerts(data)      # 임박 즉시 알림 ← 추가    
    send_spike_alerts(data)




if __name__ == "__main__":

    try:
        main()

    except Exception as e:

        send_error(str(e))

        raise