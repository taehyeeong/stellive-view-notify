# cafe_runner.py — 본 실행이 남긴 카페 대기 목록을 간격 두고 등록
# 성공 → 카드 + "✅ 카페 API 성공" / 실패·시간 초과 → 수동용 메시지
import json
import os
import time

import main as bot
from cafe import post_to_cafe, cafe_ready
from config import CAFE_POST_ENABLED, CAFE_POST_DELAY, CAFE_TIME_BUDGET


def _post(item):
    try:
        card = bot.make_card(item["video_id"], item["card_info"])
    except Exception as e:
        print(f"⚠️ 카드 생성 실패 → 이미지 없이 등록: {e}")
        card = None
    return post_to_cafe(item["subject"], item["content"], item["headid"], card)


def run():
    try:
        with open(bot.CAFE_QUEUE_FILE, encoding="utf-8") as f:
            items = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print("📭 카페 대기 없음")
        return
    os.remove(bot.CAFE_QUEUE_FILE)          # 두 번 처리 방지

    start = time.time()
    use_api = CAFE_POST_ENABLED and cafe_ready()
    last_post = None

    for item in items:
        article_url = None
        try:
            if use_api and last_post is not None:
                wait = CAFE_POST_DELAY - (time.time() - last_post)
                if time.time() - start + max(wait, 0) > CAFE_TIME_BUDGET:
                    print("⏱️ 카페 시간 초과 → 남은 건 수동")
                    use_api = False
                elif wait > 0:
                    time.sleep(wait)

            if use_api:
                res = _post(item)
                last_post = time.time()
                if (not res["ok"] and res["busy"]
                        and time.time() - start + CAFE_POST_DELAY <= CAFE_TIME_BUDGET):
                    print("⏳ 연속 등록 제한 → 한 번 더 기다렸다 재시도")
                    time.sleep(CAFE_POST_DELAY)
                    res = _post(item)
                    last_post = time.time()
                if res["ok"]:
                    article_url = res["url"]
                    print(f"✅ 카페 등록: {article_url}")
                else:
                    print(f"⚠️ 카페 등록 실패: {res['msg']}")
                    use_api = False         # 실패하면 이번엔 API 그만 (계속 두드리면 더 막힘)
        except Exception as e:
            print(f"⚠️ 카페 처리 오류: {e}")

        if article_url:
            bot.send_cafe_done(item, article_url)
        else:
            bot.send_cafe_manual(item)


if __name__ == "__main__":
    run()