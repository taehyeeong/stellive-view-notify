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
    UNITS
)

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_TOKEN"
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


async def start(update: Update, context):

    keyboard = []

    for unit_id, unit_name in UNIT_BUTTONS.items():
    
        keyboard = []

        for unit_name in UNITS.keys():
        
            keyboard.append(
                [
                    InlineKeyboardButton(
                        unit_name,
                        callback_data=f"unit_{unit_name}"
                    )
                ]
            )

    reply_markup = InlineKeyboardMarkup(
        keyboard
    )

    await update.message.reply_text(
        "🎤 YouTube Notify 봇입니다!\n\n"
        "유닛을 선택하세요.",
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

        keyboard = []

        for unit_id, unit_name in UNIT_BUTTONS.items():
        
            keyboard.append(
                [
                    InlineKeyboardButton(
                        unit_name,
                        callback_data=unit_id
                    )
                ]
            )

    await query.edit_message_text(
        "🎤 YouTube Notify 봇입니다!\n\n"
        "유닛을 선택하세요.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    return

    if query.data.startswith("unit_"):

    unit = query.data.replace(
        "unit_",
        ""
    )
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
            "🎤 멤버를 선택하세요.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        print("5. 화면 변경 완료")



def main():

    # 봇 실행 전에 헬스체크 서버를 백그라운드로 띄운다
    threading.Thread(
        target=run_health_server,
        daemon=True
    ).start()

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
