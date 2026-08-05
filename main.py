import os
import json
import requests
from datetime import datetime

from config import (
    CHANNELS,
    VIEW_STEP,
    MUSIC_KEYWORDS,
    MILESTONES
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



# 최근 영상 가져오기

def get_videos(channel_id):

    data = youtube_get(
        "https://www.googleapis.com/youtube/v3/search",
        {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "maxResults": 50,
            "type": "video",
            "key": YOUTUBE_API_KEY
        }
    )


    videos = []

    for item in data.get("items", []):

        title = item["snippet"]["title"]

        video_id = item["id"]["videoId"]

        if is_music(title):

            videos.append({
                "id": video_id,
                "title": title
            })



    
    # 🔍 확인용 로그 추가
    print("===== 찾은 음악 영상 =====")

    if videos:
        for video in videos:
            print(video["title"])
    else:
        print("음악 영상 없음")

    print("========================")

    
    return videos



# 음악 영상 판단

def is_music(title):

    title_lower = title.lower()

    for word in MUSIC_KEYWORDS:

        if word.lower() in title_lower:
            return True

    return False



# 조회수 가져오기

def get_view_count(video_id):

    data = youtube_get(
        "https://www.googleapis.com/youtube/v3/videos",
        {
            "part": "statistics,snippet",
            "id": video_id,
            "key": YOUTUBE_API_KEY
        }
    )


    item = data["items"][0]

    views = int(
        item["statistics"]["viewCount"]
    )

    return {
        "views": views,
        "title": item["snippet"]["title"],
        "thumb": item["snippet"]["thumbnails"]["default"]["url"]
    }



# ======================
# 알림 계산
# ======================

def check_milestone(
        old,
        new,
        title
):

    alerts = []


    old_step = old // VIEW_STEP
    new_step = new // VIEW_STEP


    if new_step > old_step:

        for i in range(
            old_step + 1,
            new_step + 1
        ):

            count = i * VIEW_STEP

            alerts.append(
                f"🎉 조회수 달성!\n\n"
                f"{title}\n\n"
                f"현재 {count:,}회 돌파!"
            )


    for milestone in MILESTONES:

        if old < milestone <= new:

            alerts.append(
                f"🔥 특별 기록!\n\n"
                f"{title}\n\n"
                f"{milestone:,}회 달성!"
            )


    return alerts



# ======================
# 실행
# ======================


def main():

    data = load_data()


    for channel in CHANNELS:

        channel_id = get_channel_id(channel)

        if not channel_id:
            continue


        videos = get_videos(channel_id)


        for video in videos:

            video_id = video["id"]

            info = get_view_count(video_id)

            views = info["views"]

            title = info["title"]


            old_views = data.get(
                video_id,
                {}
            ).get(
                "views",
                views
            )


            messages = check_milestone(
                old_views,
                views,
                title
            )


            for msg in messages:
                send_telegram(msg)


            data[video_id] = {
                "title": title,
                "views": views,
                "updated": str(datetime.now())
            }


    save_data(data)



if __name__ == "__main__":
    main()
