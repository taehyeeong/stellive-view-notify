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

TELEGRAM_TOKEN = os.environ.get(
    "TELEGRAM_TOKEN"
)


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
