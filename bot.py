from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes
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

    keyboard = [
        [
            InlineKeyboardButton(
                "🌸 에버리스",
                callback_data="unit_everies"
            )
        ],
        [
            InlineKeyboardButton(
                "☁️ 유니버스",
                callback_data="unit_universe"
            )
        ],
        [
            InlineKeyboardButton(
                "✨ 클리셰",
                callback_data="unit_cliche"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(
        keyboard
    )

    await update.message.reply_text(
        "🎤 YouTube Notify 봇입니다!\n\n"
        "유닛을 선택하세요.",
        reply_markup=reply_markup
    )


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

    app.run_polling()


if __name__ == "__main__":
    main()
