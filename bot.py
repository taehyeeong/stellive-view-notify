import requests


from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

from config import (
    UNIT_BUTTONS,
    UNITS,
    BOT_TITLE,
    BOT_SELECT_UNIT_TEXT,
    BOT_SELECT_MEMBER_TEXT
)


import os
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_TOKEN"
)

TELEGRAM_CHAT_ID = os.environ.get(
    "TELEGRAM_CHAT_ID"
)

GITHUB_TOKEN = os.environ.get(
    "GITHUB_TOKEN"
)

LAST_RUN_FILE = "last_run.json"

# --- Render 포트 감지용 간단한 헬스체크 서버 ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    # 로그 노이즈 줄이기
    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


def load_last_run_id():

    try:
        with open(LAST_RUN_FILE, "r") as f:
            data = json.load(f)
            return data.get("last_run_id")

    except FileNotFoundError:
        return None



def save_last_run_id(run_id):

    with open(LAST_RUN_FILE, "w") as f:
        json.dump(
            {
                "last_run_id": run_id
            },
            f,
            indent=4
        )



LAST_RUN_FILE = "last_run_id.txt"


def save_last_run_id(run_id):

    with open(
        LAST_RUN_FILE,
        "w"
    ) as f:
        f.write(str(run_id))


def load_last_run_id():

    if not os.path.exists(LAST_RUN_FILE):
        return None

    with open(
        LAST_RUN_FILE,
        "r"
    ) as f:
        return int(f.read())


async def check_github_actions(app):

    url = (
        "https://api.github.com/repos/"
        "taehyeeong/youtube-view-notify/"
        "actions/runs?per_page=1"
    )

    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=10
    )

    print("GitHub API 상태:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        return

    data = response.json()

    run = data["workflow_runs"][0]

    current_run_id = run["id"]
    last_run_id = load_last_run_id()

    print("현재 run:", current_run_id)
    print("마지막 run:", last_run_id)

    print("결론 확인:", run["conclusion"])

    print("Workflow :", run["name"])
    print("Status   :", run["status"])
    print("Result   :", run["conclusion"])

    if run["conclusion"] in [
        "failure",
        "cancelled",
        "timed_out"
    ]:

        if current_run_id != last_run_id:

            await app.bot.send_message(
                chat_id=TELEGRAM_CHAT_ID,
                text=(
                    f"⚠️ {BOT_TITLE}\n\n"
                    f"GitHub Actions {run['conclusion']} 발생\n\n"
                    f"Workflow: {run['name']}\n"
                    f"결과: {run['conclusion']}"
                )
            )

            save_last_run_id(current_run_id)


def create_unit_keyboard():
    keyboard = []

    for name, unit_id in UNIT_BUTTONS.items():
        keyboard.append(
            [
                InlineKeyboardButton(
                    name,
                    callback_data=unit_id
                )
            ]
        )

    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context):

    print("CHAT ID:", update.effective_chat.id)

    reply_markup = create_unit_keyboard()

    await update.message.reply_text(
        f"{BOT_TITLE}\n\n"
        f"{BOT_SELECT_UNIT_TEXT}",
        reply_markup=reply_markup
    )


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    print("1. 버튼:", query.data)

    await query.answer()

    print("2. answer 완료")


    if query.data == "back_units":

        await query.edit_message_text(
            f"{BOT_TITLE}\n\n"
            f"{BOT_SELECT_UNIT_TEXT}",
            reply_markup=create_unit_keyboard()
        )

        return


    if query.data in UNITS:

        unit = query.data

        print("3. 유닛 찾음")

        keyboard = []

        for artist, artist_info in UNITS[unit].items():

            keyboard.append(
                [
                    InlineKeyboardButton(
                        artist_info["display"],
                        callback_data=f"artist_{artist}"
                    )
                ]
            )


        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ 뒤로가기",
                    callback_data="back_units"
                )
            ]
        )


        print("4. 버튼 생성 완료")


        await query.edit_message_text(
            BOT_SELECT_MEMBER_TEXT,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


        print("5. 화면 변경 완료")


async def send_telegram_message(app, text):

    await app.bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=text
    )

async def send_test_message(app):

    await send_telegram_message(
        app,
        f"✅ {BOT_TITLE}\n연결 성공"
    )

    await check_github_actions(app)


def main():

    print("🤖 Telegram bot started")

    # 봇 실행 전에 헬스체크 서버를 백그라운드로 띄운다
    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()


    app = Application.builder() \
        .token(TELEGRAM_TOKEN) \
        .build()

    app.post_init = send_test_message


    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )
    

    app.run_polling()


if __name__ == "__main__":
    main()
