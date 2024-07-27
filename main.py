import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import openai

from tokens import OPENAI_API_KEY, TELEGRAM_BOT_API_TOKEN

# Set up the OpenAI API key
openai.api_key = OPENAI_API_KEY
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

chats = {}


class Chat:
    def __init__(self, user_id):
        self.user_id = user_id
        self.messages = []
        self.questions_counter = 0


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat = Chat(chat_id)
    chats[chat_id] = chat

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Привіт! Я Stroom Bot, і я хочу зарядити тебе на вибір найкращої професії ⚡️\n"
                                        "Для початку, я хочу попросити тебе розповісти щось про себе, щоб я міг дізнатися про твої інтереси та запропонувати ті професії, яка їм відповідає.\n\n"
                                        "Ти можеш розповідати що завгодно:\n"
                                        "- Які предмети у школі тобі найбільше подобаються і чому?\n"
                                        "- Чим ти любиш займатися у вільний час?\n"
                                        "- Які таланти ти в собі помічаєш?\n"
                                        "- Які навички чи здібності в тебе розвинені найкраще?\n"
                                        "- Які проблеми в світі тобі хотілося б допомогти вирішити своїми майбутніми професійними навичками?\n"
                                        "- Які твої улюблені книги, фільми, музика, ігри або інші твори мистецтва?\n\n"
                                        "Але не обов'язково обмежувати цими питаннями. Мені дуже цікаво познайомитися "
                                        "з тобою, тому розповідай!")


async def listen_story_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat = chats[chat_id]
    print(f"chat.questions_counter: {chat.questions_counter}")

    if chat.questions_counter == 2:
        # vacancy_recommendation_message = stas_machine.get_vacancy_recommendation(chat.messages)
        chat.messages += [
            {
                "role": "user",
                "content": update.message.text,
            },
            {
                "role": "system",
                "content": "Надай пропозиції роботи базуючись на відповідях."
            },
        ]
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=chat.messages)
        response_dict = response.to_dict()
        vacancy_recommendation_message = response_dict['choices'][0]['message']['content']
        print(vacancy_recommendation_message)
        await context.bot.send_message(chat_id=chat_id,
                                       text="Дякую за розповідь! Тепер я дам тобі пораду щодо вибору професії 🌟")
        await context.bot.send_message(chat_id=chat_id,
                                       text=vacancy_recommendation_message)
        return

    if chat.questions_counter == 0:
        initial_message = {
                "role": "system",
                "content": "Ти коуч, який допомагає учням обрати професію."
                           "Не відповідай на питання не пов'язані з вибором професії."

            }
        chat.messages.append(initial_message)

    current_messages = [
        {
            "role": "user",
            "content": update.message.text,
        },
        {
            "role": "system",
            "content": "Постав уточнююче коротке питання, на базі попередніх відповідей. "
                       "Не пропонуй поки що професії."
        }
    ]
    chat.messages += current_messages

    response = openai.chat.completions.create(model="gpt-4o-mini", messages=chat.messages)

    # Convert the response to a dictionary
    response_dict = response.to_dict()

    # Access the message content
    chat_answer_dict = response_dict['choices'][0]['message']
    chat.messages.append(chat_answer_dict)
    chat_answer = chat_answer_dict['content']
    chat.questions_counter += 1

    print(chat.messages)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=chat_answer)


if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_API_TOKEN).build()

    start_handler = CommandHandler('start', start)
    listen_story_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), listen_story_gpt)

    application.add_handler(start_handler)
    application.add_handler(listen_story_handler)

    application.run_polling()
