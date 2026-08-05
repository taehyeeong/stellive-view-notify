from telegram import Update
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

    await update.message.reply_text(
        "🎤 YouTube Notify 봇입니다!"
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
