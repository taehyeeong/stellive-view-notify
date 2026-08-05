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

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_TOKEN"
)


UNITS = {
    "unit_everys": {
        "아야츠노 유니": "yuni",
        "사키하네 후야": "huya"
    },

    "unit_universe": {
        "시라유키 히나": "hina",
        "네네코 마시로": "mashiro",
        "아카네 리제": "lize",
        "아라하시 타비": "tabi"
    },

    "unit_cliche": {
        "텐코 시부키": "shibuki",
        "아오쿠모 린": "rin",
        "하나코 나나": "nana",
        "유즈하 리코": "riko"
    }
}



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
                callback_data="unit_everys"
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


async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query

    print("🔥 버튼 눌림:", query.data)

    await query.answer()

    unit = query.data

    
    if query.data == "home":

        await start(update, context)
        return


    if unit in UNITS:

        keyboard = []

        for artist, artist_id in UNITS[unit].items():

            keyboard.append(
                [
                    InlineKeyboardButton(
                        artist,
                        callback_data=f"artist_{artist_id}"
                    )
                ]
            )


        keyboard.append(
            [
                InlineKeyboardButton(
                    "⬅️ 처음으로",
                    callback_data="home"
                )
            ]
        )

        print("메뉴 생성 완료")
        await query.edit_message_text(
            "🎤 멤버를 선택하세요.",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
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

    app.add_handler(
    CallbackQueryHandler(
        button_handler
    )
)
    

    app.run_polling()


if __name__ == "__main__":
    main()
