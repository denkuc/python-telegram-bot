import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
import openai
import http.client
import json
import html
import re
import random

from tokens import OPENAI_API_KEY, TELEGRAM_BOT_API_TOKEN, JOOBLE_API_KEY

openai.api_key = OPENAI_API_KEY
jooble_key = JOOBLE_API_KEY
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# gif_url = 'https://www.icegif.com/wp-content/uploads/2023/10/icegif-826.gif'
gifs = os.listdir('./assets')
def get_random_gif():
    return './assets/' + random.choice(gifs)

gif_url = './assets/daxuran-spongebob.gif'
buy_url = 'https://secure.wayforpay.com/payment/proforientation'

chats = {}

keyboard = [
    [InlineKeyboardButton("Дізнатися чому", callback_data='Дізнатися чому')],
    [InlineKeyboardButton("Подивитися вакансії", callback_data='Подивитися вакансії')]
]


def extract_vacancy_titles(message):
    # Split the message into lines
    lines = message.split('\n')

    # Initialize an empty list to hold the titles
    vacancy_titles = []

    # Iterate over each line to process it
    for line in lines:
        # Strip leading/trailing whitespace
        line = line.strip()

        # Match lines that start with a number followed by a dot and space
        match = re.match(r'^\d+\.\s*(.*?)(?=\s*–|$)', line)

        if match:
            # Extract the title before any dash or end of line
            title = match.group(1).strip()
            vacancy_titles.append(title)

    return vacancy_titles


def fetch_and_print_vacancies(keywords):
    host = 'ua.jooble.org'
    connection = http.client.HTTPConnection(host)

    # Request headers
    headers = {"Content-type": "application/json"}

    # JSON query
    body = json.dumps({
        "keywords": keywords,
        "location": "Ukraine",
        "ResultOnPage": "1",
        "salary": "5000"
    }).encode('utf-8')

    # Make the request
    connection.request('POST', '/api/' + jooble_key, body, headers)
    response = connection.getresponse()

    # Print status
    print(response.status, response.reason)

    # Read and decode response
    response_data = response.read().decode()

    # Clean up the response data
    response_data = html.unescape(response_data)  # Replace HTML entities like &nbsp;
    response_data = response_data.replace('&nbsp;', ' ')
    response_data = response_data.replace('\u00A0', ' ')
    response_data = response_data.replace('\r\n', ' ').replace('\t', ' ')
    response_data = re.sub(r'\\[rnt]', ' ', response_data)

    # Load JSON data
    json_data = json.loads(response_data)

    vacancies = []
    if 'jobs' in json_data:
        for job in json_data['jobs'][:1]:
            vacancy_info = {
                'title': job.get('title', 'No title'),
                'location': job.get('location', 'No location'),
                'salary': job.get('salary', 'No salary'),
                'link': job.get('link', 'No link')
            }
            vacancies.append(vacancy_info)
    else:
        vacancies.append({'message': "На жаль, вакансій не знайдено."})

    connection.close()

    return vacancies


class Chat:
    def __init__(self, user_id):
        self.user_id = user_id
        self.messages = []
        self.questions_counter = 0
        self.info_counter = 0
        self.explanation = ""
        self.vacancy_titles = []
        self.clicked_buttons = set()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat = Chat(chat_id)
    chats[chat_id] = chat

    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="***Привіт\\! Я Stroom Bot***⚡️\n\n"
                                        "Я хочу зарядити тебе на вибір найкращої професії\\. Для початку, я попрошу тебе розповісти щось про себе, щоб я міг дізнатися про твої інтереси та запропонувати ті професії, яка їм відповідає\\.\n\n"
                                        "Ти можеш розповідати що завгодно:\n"
                                        "\\- Що тобі найбільше подобається і чому?\n"
                                        "\\- Чим ти любиш займатися у вільний час?\n"
                                        "\\- Які таланти ти в собі помічаєш?\n"
                                        "\\- Які проблеми в світі тобі хотілося б допомогти вирішити?\n"
                                        "\\- Які твої улюблені книги, фільми, музика або ігри?\n\n"
                                        "І не обов'язково обмежуватися цими питаннями\\. Мені дуже цікаво познайомитися з тобою, тому розповідай\\!",
                                   parse_mode='MarkdownV2'
                                   )


async def listen_story_gpt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat = chats[chat_id]
    print(f"chat.questions_counter: {chat.questions_counter}")

    # Assess relevance of previous answer if it exists
    if chat.messages and chat.messages[-1]['role'] == 'assistant':
        assessment_messages = [
            {"role": "system",
             "content": "You are an AI assistant tasked with determining if the previous response provides relevant information for career guidance. Respond with only 'Yes' or 'No'."},
            {"role": "user",
             "content": f"Does this response provide relevant information that can help make recommendations in career guidance? '{chat.messages[-1]['content']}'"}
        ]
        assessment_response = openai.chat.completions.create(model="gpt-4o-mini", messages=assessment_messages)
        print("Assessment: ", assessment_response.choices[0].message.content.strip().lower())
        if assessment_response.choices[0].message.content.strip().lower() == 'yes':
            chat.info_counter += 1
        print(f"chat.info_counter: {chat.info_counter}")

    if chat and ((chat.info_counter > 0 and chat.questions_counter > 2) or chat.questions_counter > 15):
        await context.bot.send_animation(chat_id=chat_id, animation=get_random_gif(), caption='Дай подумати...')
        print(f"Кількість унікальних юзерів пройшовших тест: {len(chats.keys())}")
        chat.messages += [
            {
                "role": "user",
                "content": update.message.text,
            },
            {
                "role": "system",
                "content": "Надай пропозиції професії, що підходить особистості співрозмовника, базуючись на відповідях. Звертайся на ти. Не задавай більше питань. Не використовуй markdown"
            },
        ]
        response = openai.chat.completions.create(model="gpt-4o-mini", messages=chat.messages)
        response_dict = response.to_dict()
        vacancy_recommendation_message = response_dict['choices'][0]['message']['content']
        print(vacancy_recommendation_message)

        # Extract vacancy titles
        chat.vacancy_titles = extract_vacancy_titles(vacancy_recommendation_message)

        # Send a background prompt to ChatGPT for explanation
        explanation_prompt = [
            {
                "role": "system",
                "content": "Ти коуч, який допомагає учням обрати професію. Звертайся до співрозмовника на ти."
            },
            {
                "role": "user",
                "content": f"Надай детальне та зрозуміле пояснення, чому ти пропонуєш саме ці професії: {vacancy_recommendation_message}. Звертайся до співрозмовника на ти. Не використовуй markdown та символи * у відповіді"
            }
        ]
        explanation_response = openai.chat.completions.create(model="gpt-4o-mini", messages=explanation_prompt)
        explanation_dict = explanation_response.to_dict()
        chat.explanation = explanation_dict['choices'][0]['message']['content']

        await context.bot.send_message(chat_id=chat_id,
                                       text=vacancy_recommendation_message)

        chat.questions_counter += 1
        # After processing, show commands
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text('Що ти хочеш зараз?', reply_markup=reply_markup)

        return

    if chat.questions_counter == 0:
        initial_message = {
            "role": "system",
            "content": "Ти професійний консультант з профорієнтації. Дізнайся про тип особистості твого співрозмовника та надай пропозиції професії, яка їм ідеально пасує, базуючись на відповідях. Не відповідай на питання, не пов'язані з вибором професії. Будь дружелюбним та звертайся до співрозмовника на ти."
        }
        chat.messages.append(initial_message)

    current_messages = [
        {
            "role": "user",
            "content": update.message.text,
        },
        {
            "role": "system",
            "content": "Постав уточнююче коротке питання, якщо це допоможе тобі визначити для них професію. Інакше задай інше питання про їх особистість та інтереси. Не пропонуй поки що професії."
        }
    ]
    chat.messages += current_messages

    response = openai.chat.completions.create(model="gpt-4o-mini", messages=chat.messages)

    response_dict = response.to_dict()
    chat_answer_dict = response_dict['choices'][0]['message']
    chat.messages.append(chat_answer_dict)
    chat_answer = chat_answer_dict['content']
    chat.questions_counter += 1

    await context.bot.send_message(chat_id=update.effective_chat.id, text=chat_answer)


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    chat_id = query.message.chat_id
    chat = chats.get(chat_id)

    if query.data == "Дізнатися чому":
        if chat and chat.explanation:
            await context.bot.send_message(chat_id=chat_id, text=chat.explanation)
        else:
            await context.bot.send_message(chat_id=chat_id, text="На жаль, пояснення немає.")
        chat.clicked_buttons.add("Дізнатися чому")

        # Create new keyboard with the other option and the new button
        new_keyboard = []
        if "Подивитися вакансії" not in chat.clicked_buttons:
            new_keyboard.append([InlineKeyboardButton("Подивитися вакансії", callback_data='Подивитися вакансії')])
            [InlineKeyboardButton("Подивитися вакансії", callback_data='Подивитися вакансії')],
        new_keyboard.append([InlineKeyboardButton("Замовити консультацію (1800 грн)", url=buy_url)])

    elif query.data == "Подивитися вакансії":
        if chat and chat.vacancy_titles:
            for title in chat.vacancy_titles:
                print(title)
                vacancies = fetch_and_print_vacancies(title)
                if vacancies and len(vacancies) > 0:
                    response = f"Вакансії для {title}:\n\n"
                    for vacancy in vacancies:
                        if 'message' in vacancy:
                            response += vacancy['message'] + "\n"
                        else:
                            response += f"Назва: {vacancy['title']}\n"
                            response += f"Місцезнаходження: {vacancy['location']}\n"
                            response += f"Зарплата: {vacancy['salary']}\n"
                            response += f"Посилання: {vacancy['link']}\n\n"
                    await context.bot.send_message(chat_id=chat_id, text=response)
                else:
                    await context.bot.send_message(chat_id=chat_id, text="На жаль, немає доступних вакансій.")
        else:
            await context.bot.send_message(chat_id=chat_id, text="На жаль, немає доступних вакансій.")
        chat.clicked_buttons.add("Подивитися вакансії")

        new_keyboard = []
        if "Дізнатися чому" not in chat.clicked_buttons:
            new_keyboard.append([InlineKeyboardButton("Дізнатися чому", callback_data='Дізнатися чому')])
        new_keyboard.append([InlineKeyboardButton("Замовити консультацію (1800 грн)", url=buy_url)])

    else:
        await query.edit_message_text(text=f"Треба було обрати один з варіантов: {query.data}")
        return

    # Send a new message with the updated keyboard
    reply_markup = InlineKeyboardMarkup(new_keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Що ще ти хочеш зробити?", reply_markup=reply_markup)


if __name__ == '__main__':
    application = ApplicationBuilder().token(TELEGRAM_BOT_API_TOKEN).build()

    start_handler = CommandHandler('start', start)
    listen_story_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), listen_story_gpt)
    button_handler = CallbackQueryHandler(button)

    application.add_handler(start_handler)
    application.add_handler(listen_story_handler)
    application.add_handler(button_handler)

    application.run_polling()