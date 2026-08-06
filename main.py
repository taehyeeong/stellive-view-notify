import os
import json
import requests
from datetime import datetime

from config import (
    CHANNELS,
    VIEW_STEP,
    MUSIC_KEYWORDS,
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



# 플레이리스트 

def get_playlist_videos():

    videos = []

    seen = set()

    checked_artists = []
    checked_units = []
    checked_playlists = 0
    error_playlists = 0

    for unit, artists in UNITS.items():

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


        print(
        f"👥 확인 아티스트: {len(checked_artists)}명"
            )
    
    print(
        f"📁 확인 플레이리스트: {checked_playlists}개"
            )
    
    print(
        f"⚠️ 오류 플레이리스트: {error_playlists}개"
            )

    return videos, checked_playlists, checked_units, checked_artists


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



def get_artist_info(artist):

    for unit, artists in UNITS.items():

        if artist in artists:
            return artists[artist]

    return None



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
            send_telegram_photo(
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
            "views": views,
            "notified": list(set(notified)),
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
