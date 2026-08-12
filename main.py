import os
import json
import requests
from datetime import datetime, timezone, timedelta


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
    INITIAL_SETUP,
    UNITS
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



def send_notification(
    message,
    video_id=None
):

    if video_id:

        send_telegram_photo(
            message,
            video_id
        )

    else:

        send_telegram(
            message
        )



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

def youtube_get(url, params):

    r = requests.get(
        url,
        params=params,
        timeout=10
    )

    r.raise_for_status()

    return r.json()



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



def find_artist_from_title(title):
    title_lower = title.lower()
    candidates = []

    for unit, artists in UNITS.items():

        if unit == "스텔라이브":
            continue

        for artist_name, info in artists.items():

            aliases = info.get(
                "aliases",
                [
                    artist_name,
                    info.get("display", artist_name)
                ]
            )

            for alias in aliases:

                if alias.lower() in title_lower:
                    candidates.append(
                        (
                            len(alias),
                            artist_name,
                            unit
                        )
                    )

    if not candidates:
        return None, None

    # 긴 별칭을 우선 선택
    _, artist_name, unit = max(
        candidates,
        key=lambda item: item[0]
    )

    return artist_name, unit




# =========================
# 음악 영상 제외 판단
# =========================

def is_excluded(title):

    title_lower = title.lower()

    for word in EXCLUDE_KEYWORDS:

        if word.lower() in title_lower:
            return True

    return False



# 플레이리스트

def get_playlist_videos():

    videos = []
    seen = set()

    checked_artists = []
    checked_units = []
    checked_playlists = 0
    error_playlists = 0

    # ==========================================
    # 1단계: 멤버 개인 재생목록
    # ==========================================

    normal_units = {
        unit: artists
        for unit, artists in UNITS.items()
        if unit != "스텔라이브"
    }

    for unit, artists in normal_units.items():

        if unit not in checked_units:
            checked_units.append(unit)

        for artist_name, info in artists.items():

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
                            params
                        )

                        for item in data.get("items", []):

                            snippet = item["snippet"]

                            video_id = (
                                snippet["resourceId"]["videoId"]
                            )

                            title = snippet["title"]

                            if video_id in seen:
                                continue

                            if is_excluded(title):
                                continue

                            videos.append({
                                "id": video_id,
                                "title": title,
                                "artist": artist_name,
                                "unit": unit,
                                "playlist_id": playlist_id
                            })

                            seen.add(video_id)

                        next_page = data.get("nextPageToken")

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

    # ==========================================
    # 2단계: 스텔라이브 본계 fallback
    # ==========================================

    stellive_info = UNITS.get(
        "스텔라이브",
        {}
    ).get(
        "스텔라이브",
        {}
    )

    if "스텔라이브" not in checked_units:
        checked_units.append("스텔라이브")

    for playlist_id in stellive_info.get("playlists", []):

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
                    params
                )

                for item in data.get("items", []):

                    snippet = item["snippet"]

                    video_id = (
                        snippet["resourceId"]["videoId"]
                    )

                    title = snippet["title"]

                    # 개인 재생목록에서 이미 발견된 영상이면 유지
                    if video_id in seen:
                        continue

                    if is_excluded(title):
                        continue

                    # 제목으로 실제 멤버 판별
                    artist_name, unit = (
                        find_artist_from_title(title)
                    )

                    if artist_name is None:

                        print(
                            "⚠️ 본계 영상 아티스트 판별 실패:"
                        )
                        print(f"   영상 ID: {video_id}")
                        print(f"   제목: {title}")

                        continue

                    videos.append({
                        "id": video_id,
                        "title": title,
                        "artist": artist_name,
                        "unit": unit,
                        "playlist_id": playlist_id
                    })

                    seen.add(video_id)

                next_page = data.get("nextPageToken")

                if not next_page:
                    break

        except Exception as e:

            error_playlists += 1

            send_telegram(
                f"⚠️ 본계 플레이리스트 오류\n\n"
                f"📁 Playlist ID: {playlist_id}\n\n"
                f"❌ 내용:\n{e}"
            )

    print("===== Playlist 음악 영상 =====")

    for video in videos:
        print(
            f"[{video['artist']}] "
            f"{video['title']}"
        )

    print("총", len(videos), "개")
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


    old_step = old_views // VIEW_STEP
    new_step = views // VIEW_STEP


    if new_step > old_step:

        for i in range(
            old_step + 1,
            new_step + 1
        ):
    
            count = i * VIEW_STEP
    
            if count not in notified:
    
                alerts.append(
                    {
                        "message": MILESTONE_TEMPLATE.format(
                            keyword=artist_info["keyword"],
                            nickname=artist_info["nickname"],
                            title=title,
                            views_text=f"{count / 10000:g}만",
                            url=url
                        ),
                        "video_id": video_id
                    }
                )

            new_notified.append(count)

    for milestone in MILESTONES:

        if old_views < milestone <= views:

           alerts.append(
                {
                    "message": MILESTONE_TEMPLATE.format(
                        keyword=artist_info["keyword"],
                        nickname=artist_info["nickname"],
                        title=title,
                        views_text=f"{milestone / 10000:g}만",
                        url=url
                    ),
                    "video_id": video_id
                }
            )


    return alerts, new_notified


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


# ======================
# 실행
# ======================

def main():

    checked_playlists = 0
    error_playlists = 0
    new_videos = 0

    data = load_data()
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

        artist = video["artist"]

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
                f"👤 {artist}\n\n"
                f"🎵 {title}\n\n"
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


        if is_new:

            messages = []
            new_notified = []

        else:


            artist_info = get_artist_info(artist)
            
            messages, new_notified = check_milestone(
                old_views,
                views,
                title,
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
        
        
        data[video_id] = {
            "title": title,
            "artist": video.get("artist", ""),
            "unit": video.get("unit", ""),
            "views": views,
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
    save_data(data)



if __name__ == "__main__":

    try:
        main()

    except Exception as e:

        send_error(
            str(e)
        )

        raise
