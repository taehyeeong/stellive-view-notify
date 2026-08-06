from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler          # ← 추가
)

import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

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


# --- 헬스체크 서버 ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, format, *args):
        return


def run_health_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()


async def start(update: Update, context):
    keyboard = [
        [InlineKeyboardButton("🌸 에버리스", callback_data="unit_everys")],
        [InlineKeyboardButton("☁️ 유니버스", callback_data="unit_universe")],
        [InlineKeyboardButton("✨ 클리셰", callback_data="unit_cliche")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🎤 YouTube Notify 봇입니다!\n\n유닛을 선택하세요.",
        reply_markup=reply_markup
    )


# --- 버튼 처리기 (이게 없어서 버튼이 안 먹었던 부분) ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    print("1. 버튼:", query.data)
    await query.answer()
    print("2. answer 완료")

    unit = query.data
    if unit in UNITS:
        print("3. 유닛 찾음")
        keyboard = []
        for artist, artist_id in UNITS[unit].items():
            keyboard.append(
                [InlineKeyboardButton(artist, callback_data=f"artist_{artist_id}")]
            )
        print("4. 버튼 생성 완료")
        await query.edit_message_text(
            "🎤 멤버를 선택하세요.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        print("5. 화면 변경 완료")


def main():
    threading.Thread(target=run_health_server, daemon=True).start()

    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))   # ← 추가
    app.run_polling()


if __name__ == "__main__":
    main()
