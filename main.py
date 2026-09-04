import dataclasses
import dataclasses
import dataclasses
import os
import json
import requests
import re
import time
from datetime import datetime, timezone, timedelta

from requests import RequestException


KST = timezone(timedelta(hours=9))

def now_kst():
    return datetime.now(KST).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


from config import (
    VIEW_STEP,
    MILESTONES,
    MILESTONE_TEMPLATE,
    EXCLUDE_KEYWORDS,
    STELLIVE_EXCLUDED_ARTIST_ALIASES,  
    INITIAL_SETUP,
    UNITS,
    MAX_GROWTH_PLAYLIST_VIDEOS,
    GROWTH_PLAYLIST_ID
)


# ======================
# 환경 변수
# ======================

YOUTUBE_API_KEY = os.environ["YOUTUBE_API_KEY"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


# ======================
# 파일 저장
# ======================

DATA_FILE = "views.json"
# 조회수 변화 기록
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

def send_telegram(message):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": True
        },
        timeout=10
    )

    print("===== Telegram 결과 =====")
    print(response.status_code)
    print(response.text)
    print("========================")

def send_telegram_photo(message, video_id):

    url = (
        f"https://api.telegram.org/"
        f"bot{TELEGRAM_TOKEN}/sendPhoto"
    )

    thumbnail = (
        f"https://img.youtube.com/vi/"
        f"{video_id}/maxresdefault.jpg"
    )

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": thumbnail,
            "caption": message
        },
        timeout=10
    )

    print("===== Telegram Photo 결과 =====")
    print(response.status_code)
    print(response.text)
    print("==============================")

    return response.ok

def send_notification(message, video_id=None):

    if video_id and send_telegram_photo(message, video_id):
        return

    send_telegram(message)


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

    # 일반 조회수 단계
    step = views // VIEW_STEP

    for i in range(1, step + 1):
        reached.append(i * VIEW_STEP)


    # 특별 기록
    for milestone in MILESTONES:
        if views >= milestone:
            reached.append(milestone)


    return list(set(reached))



# ======================
# YouTube API
# ======================

def youtube_get(url, params, description="YouTube API 요청", max_retries=4):
    """YouTube API 요청. 일시 오류는 exponential backoff로 재시도하고 quota 초과는 즉시 알림."""

    for attempt in range(max_retries + 1):
        try:
            response = requests.get(
                url,
                params=params,
                timeout=10
            )
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

        # quota 초과는 재시도하지 않음
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
                message = (
                    "🚨 YouTube API quota 초과\n\n"
                    f"🕒 시간: {now_kst()}\n"
                    f"📌 요청: {description}\n\n"
                    "⛔ 오늘의 API quota가 초과되어 실행을 중단했습니다."
                )
                print(message)
                send_telegram(message)
                raise RuntimeError("YouTube API quotaExceeded")

        # YouTube 서버의 일시적인 오류는 재시도
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

        # 그 외 HTTP 오류
        try:
            response.raise_for_status()
        except RequestException as e:
            raise RuntimeError(
                f"YouTube API 오류: HTTP {response.status_code}: {description}: {e}"
            ) from e

        return response.json()


# 채널 ID 가져오기

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

    for unit, artists in UNITS.items():

        for artist_name in artists.keys():

            if artist_name in artist_names:
                ordered_names.append(
                    artist_name
                )

    return ordered_names





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
# 플레이리스트
# =========================

def add_title_artists(video, title):

    for artist_name in get_artists_from_title(title):

        if artist_name not in video["artists"]:
            video["artists"].append(artist_name)

    video["artists"] = sort_artists_by_config_order(
        video["artists"]
    )

def get_playlist_videos():

    videos = {}

    checked_artists = []
    checked_units = []
    checked_playlists = 0
    error_playlists = 0

    # ==========================================
    # 1단계
    # 개인 재생목록 먼저 확인
    # ==========================================

    for unit, artists in UNITS.items():

        # 스텔라이브 본계는 나중에 확인
        if unit == "스텔라이브":
            continue

        if unit not in checked_units:
            checked_units.append(unit)

        for artist_name, info in artists.items():

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

                            video_id = (
                                item["snippet"]
                                ["resourceId"]
                                ["videoId"]
                            )

                            title = (
                                item["snippet"]
                                ["title"]
                            )

                            if is_excluded(title):
                                continue

                            # ----------------------------------
                            # 처음 발견한 영상
                            # ----------------------------------

                            if video_id not in videos:

                                videos[video_id] = {
                                    "id": video_id,
                                    "title": title,
                                    "artists": [artist_name],
                                    "unit": unit,
                                    "is_stellive": False
                                }

                            # ----------------------------------
                            # 다른 멤버 재생목록에도 있는 영상
                            # ----------------------------------

                            else:

                                if (
                                    artist_name
                                    not in videos[video_id]["artists"]
                                ):

                                    videos[video_id]["artists"].append(
                                        artist_name
                                    )

                            add_title_artists(
                                videos[video_id],
                                title
                            )

                        next_page = data.get(
                            "nextPageToken"
                        )

                        if not next_page:
                            break

                except Exception as e:

                    error_playlists += 1

                    send_telegram(
                        f"⚠️ 플레이리스트 오류\n\n"
                        f"🎤 아티스트: {artist_name}\n"
                        f"📁 Playlist ID: {playlist_id}\n\n"
                        f"❌ 내용:\n{e}"
                    )

                    continue


    # ==========================================
    # 2단계
    # 스텔라이브 본계 재생목록 확인
    # ==========================================

    stellive_artists = UNITS.get(
        "스텔라이브",
        {}
    )

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

                        video_id = (
                            item["snippet"]
                            ["resourceId"]
                            ["videoId"]
                        )

                        title = (
                            item["snippet"]
                            ["title"]
                        )

                        if is_excluded(title):
                            continue

                        # ----------------------------------
                        # 이미 개인 재생목록에서 발견했다면
                        # 개인 정보를 그대로 유지
                        # ----------------------------------

                        if video_id in videos:

                            add_title_artists(
                                videos[video_id],
                                title
                            )

                            videos[video_id]["is_stellive"] = False

                            continue

                        # ----------------------------------
                        # 개인 재생목록에는 없었던 영상
                        # → 스텔라이브 영상으로 등록
                        # ----------------------------------

                        if is_excluded(title):
                            continue

                        # 졸업생 아이리 칸나는 공식 재생목록에 있어도 집계하지 않음
                        if is_excluded_stellive_video(title):
                            continue

                        # 개인 재생목록에서 이미 발견한 경우에는
                        # 기존의 개인/다중 멤버 정보를 유지
                        if video_id in videos:
                            continue

                        # 개인 재생목록에는 없지만 공식 커버곡 목록에 있는 경우:
                        # 제목의 멤버명으로 개인 또는 다중 멤버를 복원
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
                            # 제목에도 멤버가 없을 때만 단체 영상
                            videos[video_id] = {
                                "id": video_id,
                                "title": title,
                                "artists": ["스텔라이브"],
                                "unit": "스텔라이브",
                                "is_stellive": True
                            }

                    next_page = data.get(
                        "nextPageToken"
                    )

                    if not next_page:
                        break

            except Exception as e:

                error_playlists += 1

                send_telegram(
                    f"⚠️ 플레이리스트 오류\n\n"
                    f"🎤 아티스트: {artist_name}\n"
                    f"📁 Playlist ID: {playlist_id}\n\n"
                    f"❌ 내용:\n{e}"
                )

                continue


    # ==========================================
    # 리스트 형태로 변환
    # ==========================================

    videos = list(videos.values())


    # ==========================================
    # 결과 출력
    # ==========================================

    print("===== Playlist 음악 영상 =====")

    for video in videos:

        print(
            f"[{', '.join(video['artists'])}] "
            f"{video['title']}"
        )

    print(
        "총",
        len(videos),
        "개"
    )

    print("============================")

    print(
        f"👥 확인 아티스트: "
        f"{len(checked_artists)}명"
    )

    print(
        f"📁 확인 플레이리스트: "
        f"{checked_playlists}개"
    )

    print(
        f"⚠️ 오류 플레이리스트: "
        f"{error_playlists}개"
    )

    return (
        videos,
        checked_playlists,
        checked_units,
        checked_artists
    )


# =========================
# 조회수 가져오기
# =========================

def get_view_counts(video_ids):

    result = {}

    # YouTube API는 한 번에 최대 50개까지 조회 가능
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

            thumbnails = snippet.get(
                "thumbnails",
                {}
            )

            thumbnail = (
                thumbnails.get("high")
                or thumbnails.get("medium")
                or thumbnails.get("default")
                or {}
            ).get("url", "")

            result[video_id] = {
                "views": int(
                    statistics.get("viewCount", 0)
                ),
                "title": snippet.get(
                    "title",
                    ""
                ),
                "thumb": thumbnail
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
                    candidates.append(
                        (updated, item["views"])
                    )

            except Exception:
                continue

        if not candidates:
            return None

        candidates.sort(
            key=lambda x: x[0],
            reverse=True
        )

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

    speeds = [
        speed
        for speed in [
            daily_1d,
            daily_3d,
            daily_7d
        ]
        if speed > 0
    ]

    if speeds:
        daily_avg = (
            daily_1d * 0.50
            + daily_3d * 0.30
            + daily_7d * 0.20
        )
    else:
        daily_avg = 0

    # 다음 5만 단위 목표
    next_target = (
        (views // VIEW_STEP) + 1
    ) * VIEW_STEP

    remaining = next_target - views

    # 예상 달성 시간
    if daily_avg > 0:
        eta_days = remaining / daily_avg
    else:
        eta_days = float("inf")

    # 최근 속도가 장기 속도보다 빨라지고 있는지
    if daily_7d > 0:
        acceleration = (
            daily_1d / daily_7d
        )
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
    """
    다음 5만 단위 조회수 달성 가능성을 점수화
    """

    remaining = growth["remaining"]

    daily_1d = growth["daily_1d"]
    daily_3d = growth["daily_3d"]
    daily_7d = growth["daily_7d"]

    acceleration = growth["acceleration"]


    # ==================================
    # 1. 최근 조회수 증가 속도
    # ==================================

    # 최근 1일을 가장 중요하게 봄
    speed = (
        daily_1d * 0.50
        + daily_3d * 0.30
        + daily_7d * 0.20
    )


    if speed <= 0:
        return 0


    # ==================================
    # 2. 다음 목표까지 남은 거리
    # ==================================

    # 5만 단위 안에서 얼마나 진행됐는지
    progress = (
        1
        - (remaining / VIEW_STEP)
    )

    progress = max(
        0,
        min(1, progress)
    )


    # 가까울수록 급격하게 높은 점수
    distance_score = (
        progress ** 2
    ) * 100


    # ==================================
    # 3. 실제 예상 달성 시간
    # ==================================

    eta_days = remaining / speed


    # 1일 이내 달성 가능성을 특히 높게 평가
    if eta_days <= 1:
        eta_score = 100

    elif eta_days <= 3:
        eta_score = (
            100
            - (eta_days - 1) * 20
        )

    elif eta_days <= 7:
        eta_score = (
            60
            - (eta_days - 3) * 8
        )

    else:
        eta_score = max(
            0,
            28 - (eta_days - 7) * 2
        )


    eta_score = max(
        0,
        min(100, eta_score)
    )


    # ==================================
    # 4. 조회수 상승 속도 점수
    # ==================================

    # 하루 10만 증가 = 100점
    speed_score = min(
        100,
        speed / 1000
    )


    # ==================================
    # 5. 상승세 보너스
    # ==================================

    acceleration_bonus = 0

    if acceleration > 1.2:
        acceleration_bonus = 10

    elif acceleration > 1.05:
        acceleration_bonus = 5

    elif acceleration < 0.7:
        acceleration_bonus = -10


    # ==================================
    # 최종 점수
    # ==================================

    score = (
        distance_score * 0.35
        + eta_score * 0.40
        + speed_score * 0.20
        + acceleration_bonus
    )


    return round(
        max(0, min(100, score)),
        2
    )



# ======================
# 알림용 정보 생성
# ======================

def get_notification_artist_info(artist_names):

    artist_infos = [
        get_artist_info(artist_name)
        for artist_name in artist_names
    ]

    artist_infos = [
        info
        for info in artist_infos
        if info is not None
    ]

    return {
        "keyword": " ".join(
            info["keyword"]
            for info in artist_infos
        ),
        "nickname": " ".join(
            info["nickname"]
            for info in artist_infos
        )
    }

# ======================
# 알림 계산
# ======================

def check_milestone(
    old_views,
    views,
    title,
    url,
    notified,
    artist_info,
    video_id
):

    alerts = []
    new_notified = []

    keywords = artist_info["keyword"]
    nicknames = artist_info["nickname"]

    old_step = old_views // VIEW_STEP
    new_step = views // VIEW_STEP

    # ==================================
    # 일반 조회수 알림
    # ==================================

    if new_step > old_step:

        for i in range(
            old_step + 1,
            new_step + 1
        ):

            count = i * VIEW_STEP

            # 특별 기록과 중복되는 일반 알림은 보내지 않음
            if count in MILESTONES:
                continue

            if count not in notified:

                alerts.append(
                    {
                        "message": MILESTONE_TEMPLATE.format(
                            keyword=keywords,
                            nickname=nicknames,
                            title=title,
                            views_text=f"{count / 10000:g}만",
                            url=url
                        ),
                        "video_id": video_id
                    }
                )

            # 이미 알림을 보냈어도 목록에는 기록
            new_notified.append(count)

    # ==================================
    # 특별 조회수 알림
    # ==================================

    for milestone in set(MILESTONES):

        if (
            old_views < milestone <= views
            and milestone not in notified
        ):

            alerts.append(
                {
                    "message": MILESTONE_TEMPLATE.format(
                        keyword=keywords,
                        nickname=nicknames,
                        title=title,
                        views_text=f"{milestone / 10000:g}만",
                        url=url
                    ),
                    "video_id": video_id
                }
            )

        # 특별 기록도 알림 완료 목록에 저장
        if old_views < milestone <= views:
            new_notified.append(milestone)

    return alerts, new_notified



# ======================
# 성장 가능성 높은 영상 선정
# ======================

def get_top_growth_videos(data, limit=None):
    candidates = []

    if limit is None:
        limit = MAX_GROWTH_PLAYLIST_VIDEOS

    for video_id, info in data.items():

        if video_id.startswith("_"):
            continue

        if not isinstance(info, dict):
            continue

        if "growth" not in info:
            continue

        score = info.get("growth_score", 0)
        views = info.get("views", 0)

        artists = info.get("artists", [])

        if not isinstance(artists, list):
            artists = []

        artists = sort_artists_by_config_order(
            list(dict.fromkeys(artists))
        )

        candidates.append({
            "video_id": video_id,
            "title": info.get("title", ""),
            "artists": artists,
            "unit": info.get("unit", ""),
            "views": views,
            "score": score,
            "eta_days": info["growth"].get("eta_days")
        })

    candidates.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return candidates[:limit]


def clean_song_title(title, artist_names=None):

    cleaned = title.strip()

    # 영상 앞에 붙는 4K / 4K60 / 4K 60FPS 등의 촬영/화질 표기 제거
    cleaned = re.sub(
        r"^\s*(?:\[?\s*)4k(?:\s*[-_]?\s*(?:60(?:fps)?|120(?:fps)?))?(?:\s*\]?\s*)[|:/_-]?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    # Playlist는 원본 제목을 유지
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

    # [하나코 나나] 같은 앞쪽 멤버 표기만 제거
    if name_pattern:
        cleaned = re.sub(
            rf"^\s*[\[［(（]\s*(?:{name_pattern})\s*[\]］)）]\s*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

    # Cover 이후의 크레딧 제거
    cleaned = re.split(
        r"\s*(?:cover|歌ってみた|カバー)\b",
        cleaned,
        maxsplit=1,
        flags=re.IGNORECASE
    )[0].strip()

    # "/ 멤버명", "- 멤버명" 등 업로더/보컬 크레딧 제거
    if name_pattern:
        cleaned = re.split(
            rf"\s*(?:/|ㅣ|-)\s*.*?(?:{name_pattern}).*$",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE
        )[0].strip()

    # 제목 뒤 원곡/작곡가 표기 제거:
    # 모니터링 [モニタリング - DECO*27] → 모니터링
    cleaned = re.sub(
        r"\s*[\[［(（][^\]］)）]*[\]］)）]\s*$",
        "",
        cleaned
    ).strip()

    # 닫히지 않은 대괄호도 남기지 않음
    cleaned = re.sub(
        r"\s*[\[［][^\]］]*$",
        "",
        cleaned
    ).strip()

    return cleaned.strip(
        " \t-'\"'‘’“”「」『』[]［］()（）"
    )


# =========================
# 아티스트 설정 가져오기
# =========================

def get_artist_info(artist_name):

    for unit, artists in UNITS.items():

        if artist_name in artists:
            return artists[artist_name]

    raise ValueError(
        f"등록되지 않은 아티스트입니다: {artist_name}"
    )


def get_artists_from_title(title):

    title_lower = title.lower()
    matched_artists = []

    for unit, artists in UNITS.items():

        if unit == "스텔라이브":
            continue

        for artist_name, artist_info in artists.items():

            aliases = [
                artist_name,
                artist_info.get("display", artist_name),
                artist_info.get("keyword", ""),
                artist_info.get("nickname", ""),
                *artist_info.get("aliases", [])
            ]

            if any(
                isinstance(alias, str)
                and alias.strip()
                and alias.strip().lower() in title_lower
                for alias in aliases
            ):
                matched_artists.append(artist_name)

    return sort_artists_by_config_order(
        list(dict.fromkeys(matched_artists))
    )


def is_excluded_stellive_video(title):
    title_lower = title.lower()

    excluded_aliases = list(STELLIVE_EXCLUDED_ARTIST_ALIASES)

    # 아이리 칸나는 졸업생이므로 공식 스텔라이브 재생목록에 있어도
    # 스텔라이브 집계/알림 대상으로 가져오지 않는다.
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


# ======================
# 실행
# ======================

def main():
    print("🔥 NEW MAIN.PY - artists migration")

    checked_playlists = 0
    error_playlists = 0
    new_videos = 0

    data = load_data()

    # 구형 artist 필드 제거
    for video_id, info in data.items():
        if video_id.startswith("_"):
            continue

        if isinstance(info, dict):
            info.pop("artist", None)

    checked_videos = 0

    videos, checked_playlists, checked_units, checked_artists = get_playlist_videos()


    video_ids = [
        video["id"]
        for video in videos
    ]

    view_data = get_view_counts(
            video_ids
        )


    for video in videos:

        checked_videos += 1

        video_id = video["id"]

        info = view_data.get(video_id)

        if info is None:
            print(
                f"⚠️ YouTube API에서 영상을 찾을 수 없음: {video_id}"
            )
            continue
        
        views = info["views"]
        
        title = info["title"]

        artists = video.get("artists", [])

        if not artists:
            artists = ["스텔라이브"]

        # 이미 views.json에 저장된 제목은 사용자가 직접 수정했을 수도 있으므로
        # 절대 다시 필터링/덮어쓰기하지 않는다.
        stored_title = data.get(video_id, {}).get("title")

        if isinstance(stored_title, str) and stored_title.strip():
            display_title = stored_title.strip()
        else:
            display_title = clean_song_title(
                title,
                artists
            )

        artist_info = get_notification_artist_info(
            artists
        )

        url = (
            f"https://www.youtube.com/watch?v={video_id}"
        )


        # 새 영상인지 확인
        is_new = video_id not in data


        # 새 음악 영상 알림

        if is_new:
            new_videos += 1
        
        if is_new and not INITIAL_SETUP:

            send_photo(
                info["thumb"],

                f"🆕 새로운 음악 영상 발견!\n\n"
                f"👤 {', '.join(artists)}\n\n"
                f"🎵 {display_title}\n\n"
                f"📊 현재 조회수: {views:,}회\n\n"
                f"🔗 {url}"
            )


        # 이전 조회수 가져오기
        old_views = data.get(
            video_id,
            {}
        ).get(
            "views",
            views
        )

        # ======================
        # 조회수 history 기록
        # ======================

        video_data = data.get(
            video_id,
            {}
        )

        history = video_data.get(
            "history",
            []
        )

        # 기존 history가 잘못된 형식이면 초기화
        if not isinstance(history, list):
            history = []

        # 현재 조회수 기록 추가
        history.append({
            "views": views,
            "updated": str(now_kst())
        })

        # 최근 기록만 유지
        history = history[-HISTORY_LIMIT:]


        growth = get_growth_stats(
            history,
            views
        )

        score = calculate_growth_score(
            views,
            growth
        )

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
                old_views,
                views,
                display_title,
                url,
                data.get(video_id, {}).get(
                    "notified",
                    []
                ),
                artist_info,
                video_id
            )


        for alert in messages:
            send_notification(
                alert["message"],
                alert["video_id"]
            )

        if is_new and INITIAL_SETUP:

            notified = get_reached_milestones(views)
        
        else:
        
            notified = (
                data.get(video_id, {})
                .get("notified", [])
                + new_notified
            )
        
        # 조회수 history 누적
        history = data.get(video_id, {}).get("history", [])

        history.append({
            "views": views,
            "updated": now_kst()
        })

        # 최근 7일 정도만 유지
        history = history[-200:]


        
        data[video_id] = {
            # 첫 발견 시 필터링된 제목을 저장하고, 이후에는 저장된 제목만 사용
            # 사용자가 views.json에서 직접 수정한 제목도 그대로 보존한다.
            "title": display_title,
            "artists": video.get("artists", []),
            "unit": video.get("unit", ""),
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

            "notified": list(set(notified)),
            "updated": str(now_kst())
        }


    status = (
            "✅ 이상 없음"
            if error_playlists == 0
            else
            f"⚠️ 오류 {error_playlists}개 있음"
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

    # ======================
    # 성장 가능성 높은 영상
    # ======================

    top_videos = get_top_growth_videos(
        data,
        limit=20
    )

    data["_growth_playlist"] = {
        "updated": str(now_kst()),
        "videos": [
            {
                "video_id": video["video_id"],
                "title": video["title"],
                "artist": video["artist"],
                "views": video["views"],
                "score": video["score"],
                "eta_days": video["eta_days"]
            }
            for video in top_videos
        ]
    }


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

    print("===== 성장 가능성 TOP 20 =====")

    for rank, video in enumerate(
        top_videos,
        start=1
    ):

        print(
            f"{rank}. "
            f"[{video['score']}점] "
            f"[{', '.join(video['artists'])}] "
            f"{video['title']} "
            f"({video['views']:,}회)"
        )

    print("==============================")




    save_data(data)



if __name__ == "__main__":

    try:
        main()

    except Exception as e:

        send_error(
            str(e)
        )

        raise
