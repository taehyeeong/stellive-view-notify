import os
import json
import requests
from datetime import datetime

from config import (
    CHANNELS,
    VIEW_STEP,
    MUSIC_KEYWORDS,
    MILESTONES,
    EXCLUDE_KEYWORDS,
    INITIAL_SETUP,
    ARTISTS
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
            "text": message
        },
        timeout=10
    )

    print("===== Telegram 결과 =====")
    print(response.status_code)
    print(response.text)
    print("========================")


def send_error(error):

    message = (
        "⚠️ YouTube Notify 오류 발생\n\n"
        f"🕒 시간: {datetime.now()}\n\n"
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



# 플레이리스트 

def get_playlist_videos():

    videos = []

    seen = set()

    checked_playlists = 0

    for generation, artists in ARTISTS.items():

        for artist_name, info in artists.items():
    
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
                
                                video_id = (
        
        
        
                                    
                                    item["snippet"]
                                    ["resourceId"]
                                    ["videoId"]
                                )
                
                                title = (
                                    item["snippet"]
                                    ["title"]
                                )
                
                
                                # 중복 제거
                                if video_id in seen:
                                    continue
                
                
                                # 음악 키워드 확인
                                if is_music(title):
                
                                    videos.append({
                
                                        "id": video_id,
                                    
                                        "title": title,
                                    
                                        "artist": artist_name
                                    
                                    })
                
                                    seen.add(video_id)
        
        
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
    
    
        print("===== Playlist 음악 영상 =====")
    
        for video in videos:
            print(video["title"])
    
    
        print(
            "총",
            len(videos),
            "개"
        )
    
        print("============================")


    return videos, checked_playlists




# 음악 영상 판단

def is_music(title):

    title_lower = title.lower()


    # 제외 키워드 검사

    for word in EXCLUDE_KEYWORDS:

        if word.lower() in title_lower:

            return False


    # 음악 키워드 검사

    for word in MUSIC_KEYWORDS:

        if word.lower() in title_lower:

            return True


    return False



# 조회수 가져오기

def get_view_counts(video_ids):

    result = {}

    for i in range(0, len(video_ids), 50):

        batch = video_ids[i:i+50]

        data = youtube_get(
            "https://www.googleapis.com/youtube/v3/videos",
            {
                "part": "statistics,snippet",
                "id": ",".join(batch),
                "key": YOUTUBE_API_KEY
            }
        )


        for item in data.get("items", []):

            video_id = item["id"]

            result[video_id] = {

                "views": int(
                    item["statistics"].get(
                        "viewCount",
                        0
                    )
                ),

                "title": item["snippet"]["title"],

                "thumb": (
                    item["snippet"]["thumbnails"]
                    .get("maxres", {})
                    .get(
                        "url",
                        item["snippet"]["thumbnails"]["high"]["url"]
                    )
                ),

                "published": item["snippet"]["publishedAt"],

                "likes": int(
                    item["statistics"].get(
                        "likeCount",
                        0
                    )
                )
            }


    return result



# ======================
# 알림 계산
# ======================

def check_milestone(
        old,
        new,
        title,
        url,
        notified,
        artist
):

    alerts = []
    new_notified = []


    old_step = old // VIEW_STEP
    new_step = new // VIEW_STEP


    if new_step > old_step:

        for i in range(
            old_step + 1,
            new_step + 1
        ):
    
            count = i * VIEW_STEP
    
            if count not in notified:
    
                alerts.append(
                    f"[{artist} 키워드]\n\n"
                    f"{artist}아\n"
                    f"『{title}』 {count / 10000:g}만 축하해 !!\n\n"
                    f"{url}"
                )

            new_notified.append(count)

    for milestone in MILESTONES:

        if old < milestone <= new:

           alerts.append(
                f"[{artist} 키워드]\n\n"
                f"{artist}아\n"
                f"『{title}』 {milestone / 10000:g}만 축하해 !!\n\n"
                f"{url}"
            )


    return alerts, new_notified



# ======================
# 실행
# ======================

def main():

    checked_playlists = 0
    error_playlists = 0
    new_videos = 0

    data = load_data()
    checked_videos = 0

    videos, checked_playlists = get_playlist_videos()


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

        info = view_data[video_id]

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

            messages, new_notified = check_milestone(
                old_views,
                views,
                title,
                url,
                data.get(video_id, {}).get(
                    "notified",
                    []
                ),
                artist
            )


        for msg in messages:
            send_telegram(msg)


        data[video_id] = {
            "title": title,
            "views": views,
            "notified": data.get(video_id, {}).get(
                "notified",
                []
            ) + new_notified,
            "updated": str(datetime.now())
        }


    status = (
            "✅ 이상 없음"
            if error_playlists == 0
            else
            f"⚠️ 오류 {error_playlists}개 있음"
        )
        
        
    send_telegram(
            f"✅ YouTube Notify 실행 완료\n\n"
            f"⏰ 실행 시간: {datetime.now()}\n\n"
            f"👥 확인 아티스트: {len(ARTISTS)}세대\n"
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
