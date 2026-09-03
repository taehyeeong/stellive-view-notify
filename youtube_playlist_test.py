import os
import json
import sys

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# ==================================================
# 설정
# ==================================================

PLAYLIST_ID = "PLSDVNaGEjRRs"

SCOPES = [
    "https://www.googleapis.com/auth/youtube"
]

REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN")

if not REFRESH_TOKEN:
    raise RuntimeError(
        "YOUTUBE_REFRESH_TOKEN 환경변수가 없습니다."
    )

CLIENT_SECRET_FILE = (
    "client_secret_857271381827-"
    "nd1f7sob019637o4qgnf95hnfbh72coh.apps.googleusercontent.com.json"
)

VIEWS_FILE = "views.json"


# ==================================================
# OAuth
# ==================================================

with open(CLIENT_SECRET_FILE, "r", encoding="utf-8") as f:
    client_config = json.load(f)

installed = client_config["installed"]

credentials = Credentials(
    token=None,
    refresh_token=REFRESH_TOKEN,
    token_uri=installed["token_uri"],
    client_id=installed["client_id"],
    client_secret=installed["client_secret"],
    scopes=SCOPES,
)

youtube = build(
    "youtube",
    "v3",
    credentials=credentials,
)


# ==================================================
# quota 안전 처리
# ==================================================

api_calls = 0


def execute(request, description="API 요청"):
    """API 요청을 한 번만 실행하고 quota 초과 시 즉시 중단한다."""
    global api_calls

    api_calls += 1

    try:
        return request.execute()

    except HttpError as e:
        body = str(e)

        if "quotaExceeded" in body or "dailyLimitExceeded" in body:
            print()
            print("🚨 YouTube API quota가 초과되었습니다.")
            print(f"중단된 요청: {description}")
            print(f"이번 실행에서 API 호출 수: {api_calls}")
            print("추가 API 호출을 하지 않고 즉시 종료합니다.")
            sys.exit(2)

        raise


# ==================================================
# 현재 플레이리스트 영상 가져오기
# ==================================================


def get_playlist_items():
    """
    현재 플레이리스트를 한 번 조회한다.

    중요:
    - 이 함수는 한 실행에서 필요한 경우에만 딱 한 번 호출한다.
    - maxResults=50으로 페이지당 최대 영상을 가져온다.
    """
    result = []
    next_page_token = None

    while True:
        response = execute(
            youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=PLAYLIST_ID,
                maxResults=50,
                pageToken=next_page_token,
            ),
            "플레이리스트 영상 목록 조회",
        )

        for item in response.get("items", []):
            video_id = (
                item.get("contentDetails", {})
                .get("videoId")
            )

            if not video_id:
                continue

            result.append({
                "playlist_item_id": item["id"],
                "video_id": video_id,
                "title": item.get("snippet", {}).get(
                    "title",
                    "(제목 없음)",
                ),
                "position": item.get("snippet", {}).get(
                    "position",
                    0,
                ),
            })

        next_page_token = response.get("nextPageToken")

        if not next_page_token:
            break

    result.sort(key=lambda item: item["position"])
    return result


# ==================================================
# views.json에서 목표 목록 생성
# ==================================================

with open(VIEWS_FILE, "r", encoding="utf-8") as f:
    views_data = json.load(f)

TARGET_VIDEO_IDS = [
    video_id
    for video_id, video in views_data.items()
    if (
        not video_id.startswith("_")
        and isinstance(video, dict)
        and "title" in video
        and "views" in video
        and "growth" in video
        and "growth_score" in video
    )
]

# 성장 점수가 높은 순서대로 정렬
# 동점이면 views.json에 먼저 등장한 순서를 그대로 유지한다.
TARGET_VIDEO_IDS.sort(
    key=lambda video_id: views_data[video_id].get(
        "growth_score",
        0,
    ),
    reverse=True,
)

if not TARGET_VIDEO_IDS:
    print("❌ 성장 데이터가 있는 영상이 없습니다.")
    raise SystemExit(1)


# ==================================================
# 현재 플레이리스트 단 한 번 조회
# ==================================================

playlist_list_calls_start = api_calls
current_items = get_playlist_items()
playlist_list_calls = api_calls - playlist_list_calls_start

print()
print("✅ YouTube API 인증 성공")
print(f"현재 플레이리스트 영상 수: {len(current_items)}")
print()

print("========================================")
print("현재 플레이리스트")
print("========================================")

for i, item in enumerate(current_items, 1):
    print(
        f"{i:3}. "
        f"{item['title']} "
        f"[{item['video_id']}]"
    )

print()


# ==================================================
# 변경 계획 계산
# ==================================================

current_video_ids = {
    item["video_id"]
    for item in current_items
}

target_video_ids = set(TARGET_VIDEO_IDS)

to_add = [
    video_id
    for video_id in TARGET_VIDEO_IDS
    if video_id not in current_video_ids
]

to_remove = [
    item
    for item in current_items
    if item["video_id"] not in target_video_ids
]


# ==================================================
# 변경 계획 출력
# ==================================================

print("========================================")
print("플레이리스트 변경 계획")
print("========================================")
print(f"🎯 목표 영상: {len(TARGET_VIDEO_IDS)}개")
print(f"➕ 추가: {len(to_add)}개")
print(f"➖ 삭제: {len(to_remove)}개")
print()

if to_add:
    print("➕ 추가할 영상:")
    for video_id in to_add:
        video = views_data[video_id]
        print(
            f"  - {video_id} "
            f"{video.get('title', '(제목 없음)')}"
        )
    print()

if to_remove:
    print("➖ 삭제할 영상:")
    for item in to_remove:
        print(
            f"  - {item['video_id']} "
            f"({item['title']})"
        )
    print()


# ==================================================
# 1. 탈락 영상 삭제
# ==================================================

print("========================================")
print("1. 탈락 영상 삭제")
print("========================================")

for item in to_remove:
    video_id = item["video_id"]

    print(
        f"🗑️ 삭제: {item['title']} "
        f"[{video_id}]"
    )

    execute(
        youtube.playlistItems().delete(
            id=item["playlist_item_id"]
        ),
        f"영상 삭제: {video_id}",
    )

    print("   ✅ 삭제 완료")


# ==================================================
# 메모리상 현재 목록 갱신
# ==================================================

# 삭제 때문에 API로 다시 조회하지 않는다.
removed_ids = {
    item["video_id"]
    for item in to_remove
}

current_items = [
    item
    for item in current_items
    if item["video_id"] not in removed_ids
]

current_items.sort(key=lambda item: item["position"])


# ==================================================
# 2. 새 영상 추가
# ==================================================

print()
print("========================================")
print("2. 새 영상 추가")
print("========================================")

# 삽입 자체에서 목표 위치를 지정한다.
# 따라서 추가 후 다시 playlistItems.list를 할 필요가 없다.
current_video_ids = {item["video_id"] for item in current_items}

for target_position, video_id in enumerate(TARGET_VIDEO_IDS):
    if video_id in current_video_ids:
        continue

    print(
        f"➕ 추가: {target_position + 1:3}. "
        f"{video_id}"
    )

    response = execute(
        youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": PLAYLIST_ID,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                    "position": target_position,
                }
            },
        ),
        f"영상 추가: {video_id}",
    )

    inserted_item = response.get("snippet", {})

    current_items.insert(
        min(target_position, len(current_items)),
        {
            "playlist_item_id": response["id"],
            "video_id": video_id,
            "title": inserted_item.get("title", views_data[video_id].get("title", "(제목 없음)")),
            "position": target_position,
        },
    )

    current_video_ids.add(video_id)
    print("   ✅ 추가 완료")


# ==================================================
# 메모리상 목록 정규화
# ==================================================

# YouTube가 삽입/삭제하면서 position을 자동으로 밀어도
# 실제 순서는 메모리에서 우리가 관리한다.
for position, item in enumerate(current_items):
    item["position"] = position


# ==================================================
# 3. 순서 변경 — 실제 필요한 영상만 UPDATE
# ==================================================

print()
print("========================================")
print("3. 필요한 영상만 순서 재배치")
print("========================================")

# video_id -> item
playlist_item_map = {
    item["video_id"]: item
    for item in current_items
}


# --------------------------------------------------
# LIS(Longest Increasing Subsequence) 계산
# --------------------------------------------------
# 현재 순서를 목표 순서와 비교했을 때 상대적으로 이미 올바른
# 순서를 유지할 수 있는 영상은 UPDATE하지 않는다.
# 결과적으로 필요한 position update 수를 최소화한다.

current_order = [
    item["video_id"]
    for item in current_items
    if item["video_id"] in target_video_ids
]

target_index = {
    video_id: index
    for index, video_id in enumerate(TARGET_VIDEO_IDS)
}

sequence = [
    target_index[video_id]
    for video_id in current_order
]

prev = [-1] * len(sequence)
tails = []
tails_indices = []

for i, value in enumerate(sequence):
    left = 0
    right = len(tails)

    while left < right:
        mid = (left + right) // 2
        if tails[mid] < value:
            left = mid + 1
        else:
            right = mid

    pos = left

    if pos == len(tails):
        tails.append(value)
        tails_indices.append(i)
    else:
        tails[pos] = value
        tails_indices[pos] = i

    if pos > 0:
        prev[i] = tails_indices[pos - 1]

keep_ids = set()

if tails_indices:
    cursor = tails_indices[-1]

    while cursor != -1:
        keep_ids.add(current_order[cursor])
        cursor = prev[cursor]

print(f"현재 순서 영상: {len(current_order)}개")
print(f"순서 유지 가능 영상: {len(keep_ids)}개")
print(
    f"필요한 position UPDATE 최대 {len(TARGET_VIDEO_IDS) - len(keep_ids)}개"
)
print()


# --------------------------------------------------
# 목표 순서로 이동
# --------------------------------------------------
# 왼쪽부터 목표 순서를 맞춘다.
# keep_ids에 들어 있는 영상은 이미 상대적 순서를 유지하므로
# UPDATE하지 않는다.
# 나머지는 필요한 위치에만 한 번씩 이동한다.

updates = 0

for target_position, video_id in enumerate(TARGET_VIDEO_IDS):
    item = playlist_item_map.get(video_id)

    if not item:
        print(f"⚠️ 영상 정보를 찾지 못함: {video_id}")
        continue

    # 이미 이 위치에 있다면 당연히 API 호출하지 않는다.
    current_position = current_items.index(item)

    if video_id in keep_ids:
        print(
            f"   유지: {target_position + 1:3}. "
            f"{video_id} (상대 순서 유지)"
        )
        continue

    if current_position == target_position:
        print(
            f"   유지: {target_position + 1:3}. "
            f"{video_id}"
        )
        continue

    print(
        f"🔄 이동: {current_position + 1:3} → "
        f"{target_position + 1:3} "
        f"{video_id}"
    )

    execute(
        youtube.playlistItems().update(
            part="snippet",
            body={
                "id": item["playlist_item_id"],
                "snippet": {
                    "playlistId": PLAYLIST_ID,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                    "position": target_position,
                },
            },
        ),
        f"영상 순서 이동: {video_id}",
    )

    # API의 position 이동 결과를 메모리에 반영한다.
    moved_item = current_items.pop(current_position)
    current_items.insert(target_position, moved_item)

    updates += 1
    print("   ✅ 이동 완료")


# ==================================================
# 4. 최종 결과 — API 재조회 없이 메모리 검증
# ==================================================

print()
print("========================================")
print("4. 최종 결과")
print("========================================")

final_video_ids = [
    item["video_id"]
    for item in current_items
]

print(f"최종 영상 수: {len(final_video_ids)}")
print(f"이번 실행 API 호출 수: {api_calls}")
print(f"  - 플레이리스트 목록 조회: {playlist_list_calls}회")
print(f"  - 삭제: {len(to_remove)}회")
print(f"  - 추가: {len(to_add)}회")
print(f"  - 순서 변경: {updates}회")
print()

for i, item in enumerate(current_items, 1):
    print(
        f"{i:3}. "
        f"{item['title']} "
        f"[{item['video_id']}]"
    )

print()
print("========================================")
print("검증 결과")
print("========================================")

if final_video_ids == TARGET_VIDEO_IDS:
    print(
        "✅ 성공: "
        "플레이리스트가 전체 성장 점수 순서와 일치합니다."
    )
else:
    print(
        "⚠️ 주의: 메모리상 최종 순서가 목표 순서와 일치하지 않습니다."
    )

    missing = [
        video_id
        for video_id in TARGET_VIDEO_IDS
        if video_id not in final_video_ids
    ]

    unexpected = [
        video_id
        for video_id in final_video_ids
        if video_id not in target_video_ids
    ]

    if missing:
        print("❌ 빠진 영상:")
        for video_id in missing:
            print(f"  - {video_id}")

    if unexpected:
        print("❌ 예상하지 않은 영상:")
        for video_id in unexpected:
            print(f"  - {video_id}")

print()
print("========================================")
print("플레이리스트 업데이트 종료")
print("========================================")
