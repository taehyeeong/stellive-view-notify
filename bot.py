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


from dotenv import load_dotenv
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

load_dotenv()

TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_TOKEN"
)

GITHUB_TOKEN = os.environ.get(
    "GITHUB_TOKEN"
)


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

def check_github_actions():

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

    print("Workflow :", run["name"])
    print("Status   :", run["status"])
    print("Result   :", run["conclusion"])


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



def main():

    print("🤖 Telegram bot started")

    # 봇 실행 전에 헬스체크 서버를 백그라운드로 띄운다
    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start

    check_github_actions()

    app = Application.builder() \
        .token(TELEGRAM_TOKEN) \
        .build()

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
