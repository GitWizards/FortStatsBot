import os
import logging
import csv
import urllib3
import json

from datetime import date
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (CallbackQueryHandler, Filters, CommandHandler, ConversationHandler,
                          CallbackContext, MessageHandler, Updater)
from pid import PidFile

from utils import prepare_result_msg

store_file = '.store'
http = urllib3.PoolManager()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Conversation states
GET_USERNAME, GET_ACCOUNT_TYPE, GET_TIME_WINDOW, SEND_RESULT, SEND_RESULT_LIST = range(
    5)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Hello there! 👋\n\nUse /search to search for a player "
                              "and /replay to repeat the last search.",
                              parse_mode='Markdown')
    return


def start_search(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("*Send me the username*", parse_mode="Markdown")
    return GET_USERNAME


def get_username(update: Update, context: CallbackContext) -> int:
    response = update['message']['text']
    context.user_data['username'] = response

    # Prepare keyboard
    keyboard = [["🔲 Epic"], ["🟦 PSN"], ["🟩 Xbox"]]
    markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True)

    update.message.reply_text(
        "*Which platfrom?*", reply_markup=markup, parse_mode="Markdown")
    return GET_ACCOUNT_TYPE


def get_account_type(update: Update, context: CallbackContext) -> int:
    response = update['message']['text'].lower()
    context.user_data['account_type'] = response

    # Prepare keyboard
    keyboard = [["🍃 Lifetime"], [get_json("time_window")+" Season"]]
    markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True)

    update.message.reply_text("*Lifetime data or just the current season?*",
                              reply_markup=markup,
                              parse_mode="Markdown")
    return GET_TIME_WINDOW


def get_time_window(update: Update, context: CallbackContext) -> int:
    response = update['message']['text'].lower()
    context.user_data['time_window'] = response

    # Prepare keyboard
    keyboard = [["🔢 Everything"], ["1️⃣ Solo", "2️⃣ Duo"],
                ["3️⃣ Trio", "4️⃣ Squad"], ["🔐 Limited modes"]]
    markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True)

    update.message.reply_text(
        "*Match type?*", reply_markup=markup, parse_mode="Markdown")
    return SEND_RESULT


def send_result(update: Update, context: CallbackContext) -> int:
    response = update['message']['text'].lower()
    status = 0
    if response[:2] == '🔢 ':
        context.user_data['match_type1'] = response[:2]
    else:
        context.user_data['match_type1'] = response[:3] + ' '

    if response[2:] == "everything":
        context.user_data['match_type'] = "overall"
    elif response[2:] == "limited modes":
        context.user_data['match_type'] = "ltm"
    else:
        context.user_data['match_type'] = response[4:]

    msg = prepare_result_msg(
        context.user_data['username'],
        context.user_data['account_type'][2:],
        context.user_data['time_window'][2:],
        context.user_data['match_type'],
    )

    with open(store_file, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0

        for row in csv_reader:
            if line_count == 0:
                line_count += 1
            if row["user_id"] == str(update['message']['chat']['id']):

                if row["username"] == context.user_data['username'].capitalize() and row["account_type"] == context.user_data['account_type'] and row["time_window"] == context.user_data['time_window']and row["match_type"] == context.user_data['match_type1'] + context.user_data['match_type']:
                    status = 1

            line_count += 1

    keyboard = [
        [
            InlineKeyboardButton("Save 💾", callback_data='0')
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data['remove'] = update.message.reply_text(
        msg, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

    context.user_data['remove'].delete()

    if not 'found' in msg and status != 1:
        update.message.reply_text(
            msg, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        update.message.reply_text(
            msg, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

    return ConversationHandler.END


def save_player_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    result = query['message']['reply_markup']['inline_keyboard'][0][0]['text'].lower()
    query.answer()

    if "save" in result:
        msg = prepare_result_msg(
            context.user_data['username'],
            context.user_data['account_type'][2:],
            context.user_data['time_window'][2:],
            context.user_data['match_type'],
        )

        store = '{},{},{},{},{}\n'.format(query['message']['chat']['id'], context.user_data['username'].capitalize(
        ), context.user_data['account_type'], context.user_data['time_window'], context.user_data['match_type1'] + context.user_data['match_type'])

        file = open(store_file, "a")
        file.write(store)
        file.close()

        msg = msg + "\n\n*Player saved ✅*"

        query.edit_message_text(msg, parse_mode="Markdown")
    else:
        lines = list()
        with open(store_file, 'r') as readFile:
            reader = csv.reader(readFile)
            for row in reader:
                lines.append(row)
                for field in row:
                    if field == context.user_data['username'].capitalize():
                        if row[0] == str(query['message']['chat']['id']) and context.user_data['account_type'] in row[2] and context.user_data['time_window'] in row[3] and context.user_data['match_type'] in row[4]:
                            lines.remove(row)

        with open(store_file, 'w') as writeFile:
            writer = csv.writer(writeFile)
            writer.writerows(lines)

        msg = "\n\n*Player remove ✅*"
        query.edit_message_text(msg,  parse_mode="Markdown")


def replay_last_search(update: Update, context: CallbackContext) -> None:
    try:
        msg = prepare_result_msg(
            context.user_data['username'],
            context.user_data['account_type'][2:],
            context.user_data['time_window'][2:],
            context.user_data['match_type'],
        )
    except KeyError:
        msg = "*Can't replay last search 😕*"

    update.message.reply_text(
        msg, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    return


def list_player_saved(update: Update, context: CallbackContext) -> int:

    with open(store_file, mode='r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        line_count = 0
        store = []
        for row in csv_reader:
            if line_count == 0:
                line_count += 1

            if '🔢' in row["match_type"] or '🔐' in row["match_type"]:
                row_match_type = row["match_type"][:2]
            else:
                row_match_type = row["match_type"][:3]

            if not "🍃" in row["time_window"][:2]:
                row_time_window = get_json("time_window") + " "
            else:
                row_time_window = row["time_window"][:2]

            if row["user_id"] == str(update['message']['chat']['id']):
                store.append(["{} - {}{}{}".format(
                    row["username"],  row["account_type"][:2], row_time_window, row_match_type)])
            line_count += 1

    # Prepare keyboard
    keyboard = store

    markup = ReplyKeyboardMarkup(
        keyboard, one_time_keyboard=True, resize_keyboard=True)

    if not store:
        update.message.reply_text(
            "*List player is empty 😔*", reply_markup=markup, parse_mode="Markdown")
    else:
        update.message.reply_text(
            "*Choose player*\n\n*Platfrom:*\n{}\n\n*Time Type:*\n{}\n\n*Match Type:*\n{}".format("🔲 Epic | 🟦 PSN | 🟩 Xbox", "🍃 Lifetime | "+get_json("time_window")+" Season", "🔢 Everything\n1️⃣ Solo | 2️⃣ Duo | 3️⃣ Trio | 4️⃣ Squad\n🔐 Limited modes"), reply_markup=markup, parse_mode="Markdown")
    return SEND_RESULT_LIST


def send_result_list(update: Update, context: CallbackContext) -> int:
    try:
        response = update['message']['text']

        with open(store_file, mode='r') as csv_file:
            csv_reader = csv.DictReader(csv_file)
            line_count = 0
            response = response.split(" ")

            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                context.user_data['username'] = response[0]
                context.user_data['account_type'] = response[2].replace(
                    "🔲", "Epic").replace("🟦", "PSN").replace("🟩", "Xbox").lower()

                if response[3] == "🍃":
                    context.user_data['time_window'] = response[3] = "lifetime"
                else:
                    context.user_data['time_window'] = response[3] = "season"
                context.user_data['match_type'] = response[4].replace("🔢", "overall").replace("1️⃣", "solo").replace(
                    "2️⃣", "duo").replace("3️⃣", "trio").replace("4️⃣", "squad").replace("🔐", "ltm").lower()

                line_count += 1

        msg = prepare_result_msg(
            context.user_data['username'],
            context.user_data['account_type'],
            context.user_data['time_window'],
            context.user_data['match_type'],
        )

        keyboard = [
            [
                InlineKeyboardButton("Remove 🗑", callback_data='1')
            ]
        ]

        context.user_data['remove'] = update.message.reply_text(
            msg, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")

        context.user_data['remove'].delete()

        update.message.reply_text(
            msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

        return ConversationHandler.END
    except IndexError:
        msg = "*You have not chosen a player from the list 😕*"

        update.message.reply_text(
            msg, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
        return ConversationHandler.END


def send_credits(update: Update, context: CallbackContext) -> None:
    msg = (
        "*API developed by*: [Fortnite-API](https://fortnite-api.com/)\n"
        "*Bot developed by*:\n"
        "• [Fast0n](https://github.com/fast0n)\n"
        "• [Radeox](https://github.com/radeox)"
    )

    update.message.reply_text(msg, parse_mode="Markdown")
    return


def conversation_fallback(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("*Something went wrong. Try again 😕*",
                              reply_markup=ReplyKeyboardRemove(),
                              parse_mode="Markdown")
    return ConversationHandler.END


def get_json(what):
    json_result = http.request('GET', 'https://pastebin.com/raw/HNxPB0zp')
    json_result = json.loads(json_result.data.decode('utf-8'))
    return json_result[what]


def main():
    # Load env variables
    load_dotenv()
    TOKEN = os.environ['TOKEN']

    # Setup bot
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Add command handlers
    start_handler = CommandHandler('start', start)
    replay_handler = CommandHandler('replay', replay_last_search)
    list_player_saved_handler = CommandHandler('list', list_player_saved)
    credits_handler = CommandHandler('credits', send_credits)

    search_handler = ConversationHandler(
        entry_points=[CommandHandler('search', start_search)],
        states={
            GET_USERNAME: [
                MessageHandler(Filters.text, get_username),
            ],
            GET_ACCOUNT_TYPE: [
                MessageHandler(Filters.regex(
                    '🔲 Epic|🟦 PSN|🟩 Xbox'), get_account_type),
            ],
            GET_TIME_WINDOW: [
                MessageHandler(Filters.regex(
                    '🍃 Lifetime|'+get_json("time_window")+' Season'), get_time_window),
            ],
            SEND_RESULT: [
                MessageHandler(Filters.regex('🔢 Everything|1️⃣ Solo|2️⃣ Duo|3️⃣ Trio|4️⃣ Squad|🔐 Limited modes'),
                               send_result),
            ]
        },
        fallbacks=[MessageHandler(Filters.update, conversation_fallback)],
    )

    list_player_saved_handler = ConversationHandler(
        entry_points=[CommandHandler('list', list_player_saved)],
        states={
            SEND_RESULT_LIST: [
                MessageHandler(Filters.text, send_result_list),
            ]
        },
        fallbacks=[MessageHandler(Filters.update, conversation_fallback)],
    )

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(search_handler)
    dispatcher.add_handler(CallbackQueryHandler(save_player_button))
    dispatcher.add_handler(replay_handler)
    dispatcher.add_handler(list_player_saved_handler)
    dispatcher.add_handler(credits_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    with PidFile('fort_stats_bot') as _:
        main()
