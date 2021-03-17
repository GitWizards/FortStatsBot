import os
import logging

from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (Filters, CommandHandler, ConversationHandler,
                          CallbackContext, MessageHandler, Updater)
from pid import PidFile

from utils import prepare_result_msg

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

# Conversation states
GET_USERNAME, GET_ACCOUNT_TYPE, GET_TIME_WINDOW, SEND_RESULT = range(4)


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
    keyboard = [["Epic"], ["PSN"], ["Xbox"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text("*Which platfrom?*", reply_markup=markup, parse_mode="Markdown")
    return GET_ACCOUNT_TYPE


def get_account_type(update: Update, context: CallbackContext) -> int:
    response = update['message']['text'].lower()
    context.user_data['account_type'] = response

    # Prepare keyboard
    keyboard = [["Lifetime"], ["Season"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text("*Lifetime data or just the current season?*",
                              reply_markup=markup,
                              parse_mode="Markdown")
    return GET_TIME_WINDOW


def get_time_window(update: Update, context: CallbackContext) -> int:
    response = update['message']['text'].lower()
    context.user_data['time_window'] = response

    # Prepare keyboard
    keyboard = [["Everything"], ["Solo", "Duo"], ["Trio", "Squad"], ["Limited modes"]]
    markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    update.message.reply_text("*Match type?*", reply_markup=markup, parse_mode="Markdown")
    return SEND_RESULT


def send_result(update: Update, context: CallbackContext) -> int:
    response = update['message']['text'].lower()

    if response == "everything":
        context.user_data['match_type'] = "overall"
    elif response == "limited modes":
        context.user_data['match_type'] = "ltm"
    else:
        context.user_data['match_type'] = response

    msg = prepare_result_msg(
        context.user_data['username'],
        context.user_data['account_type'],
        context.user_data['time_window'],
        context.user_data['match_type'],
    )

    update.message.reply_text(msg, reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    return ConversationHandler.END


def replay_last_search(update: Update, context: CallbackContext) -> None:
    try:
        msg = prepare_result_msg(
            context.user_data['username'],
            context.user_data['account_type'],
            context.user_data['time_window'],
            context.user_data['match_type'],
        )
    except KeyError:
        msg = "*Can't replay last search 😕*"

    update.message.reply_text(msg, parse_mode="Markdown")
    return


def send_credits(update: Update, context: CallbackContext) -> None:
    msg = ("*API developed by*: [Fortnite-API](https://fortnite-api.com/)\n"
           "*Bot developed by*: [Radeox](https://github.com/radeox)")

    update.message.reply_text(msg, parse_mode="Markdown")
    return


def conversation_fallback(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("*Something went wrong. Try again 😕*",
                              reply_markup=ReplyKeyboardRemove(),
                              parse_mode="Markdown")
    return ConversationHandler.END


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
    credits_handler = CommandHandler('credits', send_credits)

    search_handler = ConversationHandler(
        entry_points=[CommandHandler('search', start_search)],
        states={
            GET_USERNAME: [
                MessageHandler(Filters.text, get_username),
            ],
            GET_ACCOUNT_TYPE: [
                MessageHandler(Filters.regex('Epic|PSN|Xbox'), get_account_type),
            ],
            GET_TIME_WINDOW: [
                MessageHandler(Filters.regex('Lifetime|Season'), get_time_window),
            ],
            SEND_RESULT: [
                MessageHandler(Filters.regex('Everything|Solo|Duo|Trio|Squad|Limited modes'),
                               send_result),
            ]
        },
        fallbacks=[MessageHandler(Filters.update, conversation_fallback)],
    )

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(search_handler)
    dispatcher.add_handler(replay_handler)
    dispatcher.add_handler(credits_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    with PidFile('fort_stats_bot') as _:
        main()
