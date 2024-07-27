import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from openai_client import openai

telegram_bot_api_token = "TELEGRAM_BOT_API_TOKEN"
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Привіт! Я Stroom Bot, і я хочу зарядити тебе на вибір найкращої професії ⚡️\n"
                                        "Для початку, я хочу попросити тебе розповісти щось про себе, щоб я міг дізнатися про твої інтереси та запропонувати ті професії, яка їм відповідає.\n\n"
                                        "Ти можеш розповідати що завгодно:\n"
                                        "- Які предмети у школі тобі найбільше подобаються і чому?\n"
                                        "- Чим ти любиш займатися у вільний час?\n"
                                        "- Які таланти ти в собі помічаЯкі навички чи здібності в тебе розвинені найкраще?\n"
                                        "- Які проблеми в світі тобі хотілося б допомогти вирішити своїми майбутніми професійними навичками?\n"
                                        "- Які твої улюблені книги, фільми, музика, ігри або інші твори мистецтва?")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


async def chat_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Use the OpenAI API to generate a response to the user's message in Ukrainian language,
    # please limit the tokens by 1000
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": update.message.text,
            },
        ],
    )
    # Convert the response to a dictionary
    response_dict = response.to_dict()

    # Access the message content
    chat_answer = response_dict['choices'][0]['message']['content']

    await context.bot.send_message(chat_id=update.effective_chat.id, text=chat_answer)


if __name__ == '__main__':
    application = ApplicationBuilder().token(telegram_bot_api_token).build()

    start_handler = CommandHandler('start', start)
    echo_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), echo)
    chat_gpt_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), chat_gpt)

    application.add_handler(start_handler)
    application.add_handler(chat_gpt_handler)

    application.run_polling()
