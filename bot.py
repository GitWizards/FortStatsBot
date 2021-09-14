import os
import logging
import signal

from dotenv import load_dotenv
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup,
                      InlineQueryResultArticle, InputTextMessageContent,
                      ReplyKeyboardMarkup, ReplyKeyboardRemove, Update)
from telegram.ext import (CallbackContext, CallbackQueryHandler,
                          CommandHandler, ConversationHandler, Filters,
                          InlineQueryHandler, MessageHandler,
                          PicklePersistence, Updater)
from telegram.error import Conflict

from utils import MessageConverter, prepare_result_msg


# Utility to convert messages to more compact form
mc = MessageConverter()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# Conversation states
GET_USERNAME, GET_ACCOUNT_TYPE, GET_TIME_WINDOW, SEND_RESULT, SEND_RESULT_LIST = range(5)


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Hello there! 👋\n\n'
        '*Command list*:\n'
        '• /search - search for a player\n'
        '• /replay - repeat the last search\n'
        '• /list - Show previously saved searches',
        parse_mode='Markdown'
    )
    return None


def start_search(update: Update, context: CallbackContext) -> int:
    update.message.reply_text('*Send me the username*', parse_mode='Markdown')
    context.user_data['last_search'] = {}
    return GET_USERNAME


def get_username(update: Update, context: CallbackContext) -> int:
    response = update['message']['text']
    context.user_data['last_search']['username'] = response.lower()

    markup = ReplyKeyboardMarkup(
        [['🔲 Epic'], ['🟦 PSN'], ['🟩 Xbox']],
        one_time_keyboard=True,
        resize_keyboard=True
    )

    update.message.reply_text(
        '*Which platfrom?*',
        reply_markup=markup,
        parse_mode='Markdown'
    )
    return GET_ACCOUNT_TYPE


def get_account_type(update: Update, context: CallbackContext) -> int:
    response = update['message']['text']
    context.user_data['last_search']['account_type'] = mc.human_to_machine(
        response)

    markup = ReplyKeyboardMarkup(
        [['🍃 Lifetime'], [mc.season_icon + ' Season']],
        one_time_keyboard=True,
        resize_keyboard=True
    )

    update.message.reply_text(
        '*Lifetime data or just the current season?*',
        reply_markup=markup,
        parse_mode='Markdown'
    )
    return GET_TIME_WINDOW


def get_time_window(update: Update, context: CallbackContext) -> int:
    response = update['message']['text']
    context.user_data['last_search']['time_window'] = mc.human_to_machine(
        response)

    markup = ReplyKeyboardMarkup(
        [
            ['🔢 Everything'], ['1️⃣ Solo', '2️⃣ Duo'],
            ['3️⃣ Trio', '4️⃣ Squad'], ['🔐 Limited modes']
        ],
        one_time_keyboard=True,
        resize_keyboard=True
    )

    update.message.reply_text(
        '*Match type?*',
        reply_markup=markup,
        parse_mode='Markdown'
    )
    return SEND_RESULT


def send_result(update: Update, context: CallbackContext) -> int:
    # Make sure search store exists
    if 'store' not in context.user_data:
        context.user_data['store'] = []

    placeholder = update.message.reply_text(
        "*Searching...*",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )

    response = update['message']['text']
    context.user_data['last_search']['match_type'] = mc.human_to_machine(
        response)

    context.user_data['last_result'] = prepare_result_msg(
        context.user_data['last_search']['username'],
        context.user_data['last_search']['account_type'],
        context.user_data['last_search']['time_window'],
        context.user_data['last_search']['match_type'],
    )

    # Remove placeholder message
    placeholder.delete()

    # If not in saved and found some results
    if context.user_data['last_search'] not in context.user_data['store'] and "not found" not in context.user_data['last_result']:
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton('Save 💾', callback_data='save')
        ]])

    else:
        reply_markup = None

    update.message.reply_text(
        context.user_data['last_result'],
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ConversationHandler.END


def save_player_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    callback = query['message']['reply_markup']['inline_keyboard'][0][0]['callback_data']
    query.answer()

    # Make sure saved search array exists
    if context.user_data['store'] is None:
        context.user_data['store'] = []

    if callback == 'save':
        context.user_data['store'].append(
            context.user_data['last_search']
        )

        msg = f"{context.user_data['last_result']}\n\n*Player saved ✅*"
        query.edit_message_text(msg, parse_mode='Markdown')
    elif 'delete' in callback:
        index = int(callback.split('_')[1])

        context.user_data['store'].remove(
            context.user_data['store'][index]
        )

        msg = '*Player removed ✅*'
        query.edit_message_text(msg, parse_mode='Markdown')


def replay_last_search(update: Update, context: CallbackContext) -> None:
    try:
        msg = prepare_result_msg(
            context.user_data['last_search']['username'],
            context.user_data['last_search']['account_type'],
            context.user_data['last_search']['time_window'],
            context.user_data['last_search']['match_type'],
        )
    except KeyError:
        msg = '*Can\'t replay last search 😕*'

    update.message.reply_text(
        msg,
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    return None


def list_saved_players(update: Update, context: CallbackContext) -> int:
    keyboard = []

    if 'store' not in context.user_data or context.user_data['store'] == []:
        update.message.reply_text(
            '*List player is empty 😔*',
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    for i, result in enumerate(context.user_data['store'], 1):
        keyboard.append([
            f"{i} - {result['username'].capitalize()} - "
            f"{mc.machine_to_human(result['account_type']).split()[0]}"
            f"{mc.machine_to_human(result['time_window']).split()[0]}"
            f"{mc.machine_to_human(result['match_type']).split()[0]}"
        ])

    markup = ReplyKeyboardMarkup(
        keyboard,
        one_time_keyboard=True,
        resize_keyboard=True
    )

    update.message.reply_text(
        '*Choose player*\n\n'
        '*Platfrom:*\n🔲 Epic | 🟦 PSN | 🟩 Xbox\n\n'
        f'*Time Type:*\n🍃 Lifetime | {mc.season_icon} Season\n\n'
        '*Match Type:*\n🔢 Everything\n1️⃣ Solo | 2️⃣ Duo | 3️⃣ Trio | 4️⃣ Squad\n🔐 Limited modes',
        reply_markup=markup,
        parse_mode='Markdown'
    )
    return SEND_RESULT_LIST


def send_result_list(update: Update, context: CallbackContext) -> int:
    try:
        index = (int(update['message']['text'][0]) - 1)
    except ValueError:
        update.message.reply_text(
            'Something went wrong 😕',
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    placeholder = update.message.reply_text(
        "*Searching...*",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )

    try:
        msg = prepare_result_msg(
            context.user_data['store'][index]['username'],
            context.user_data['store'][index]['account_type'],
            context.user_data['store'][index]['time_window'],
            context.user_data['store'][index]['match_type'],
        )

        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton('Remove 🗑', callback_data=f'delete_{index}')
        ]])
    except IndexError:
        msg = "Something went wrong, I could not find the player 😕"
        reply_markup = ReplyKeyboardRemove()
    finally:
        placeholder.delete()

        update.message.reply_text(
            msg,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return ConversationHandler.END


def send_credits(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        '*API developed by*: [Fortnite-API](https://fortnite-api.com/)\n'
        '*Bot developed by*:\n'
        '• [Fast0n](https://github.com/fast0n)\n'
        '• [Radeox](https://github.com/radeox)',
        parse_mode='Markdown'
    )
    return None


def conversation_fallback(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        '*Something went wrong. Try again 😕*',
        reply_markup=ReplyKeyboardRemove(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


def article(id, title, description, message_text, account_type) -> InlineQueryResultArticle:
    if account_type == 'epic':
        thumb_url = 'https://raw.githubusercontent.com/FastRadeox/FortStatsBot/main/img/logo1.png'
    elif account_type == "psn":
        thumb_url = 'https://raw.githubusercontent.com/FastRadeox/FortStatsBot/main/img/logo2.png'
    else:
        thumb_url = 'https://raw.githubusercontent.com/FastRadeox/FortStatsBot/main/img/logo3.png'

    return InlineQueryResultArticle(
        id=id,
        title=title,
        description=description,
        thumb_url=thumb_url,
        input_message_content=InputTextMessageContent(
            message_text=message_text,
            parse_mode='Markdown',
        )
    )


def inlinequery(update: Update, context: CallbackContext) -> None:
    results = []

    for i, result in enumerate(context.user_data['store'], 1):
        results.append(article(
            id=i,
            title=f"{result['username'].capitalize()}",
            description=(
                f"{mc.machine_to_human(result['account_type']).split()[0]} - "
                f"{mc.machine_to_human(result['time_window']).split()[0]} - "
                f"{mc.machine_to_human(result['match_type']).split()[0]}"
            ),
            message_text=prepare_result_msg(
                result['username'],
                result['account_type'],
                result['time_window'],
                result['match_type'],

            ),
            account_type=result['account_type'],
        ))

    update.inline_query.answer(results)
    return None


def error_handler(update: object, context: CallbackContext) -> None:
    if isinstance(context.error, Conflict):
        print("[FATAL] Token conflict!")
        os.kill(os.getpid(), signal.SIGINT)
    else:
        print("[ERROR] " + str(context.error))
        pass


def main():
    # Load env variables
    load_dotenv()
    TOKEN = os.environ['TOKEN']

    # Create persistant storage
    persistence = PicklePersistence(filename='db')

    # Setup bot
    updater = Updater(TOKEN, use_context=True, persistence=persistence)
    dispatcher = updater.dispatcher

    # Add command handlers
    start_handler = CommandHandler('start', start)
    replay_handler = CommandHandler('replay', replay_last_search)
    list_saved_players_handler = CommandHandler('list', list_saved_players)
    credits_handler = CommandHandler('credits', send_credits)

    search_handler = ConversationHandler(
        entry_points=[CommandHandler('search', start_search)],
        states={
            GET_USERNAME: [
                MessageHandler(Filters.text, get_username),
            ],
            GET_ACCOUNT_TYPE: [
                MessageHandler(
                    Filters.regex('🔲 Epic|🟦 PSN|🟩 Xbox'),
                    get_account_type
                ),
            ],
            GET_TIME_WINDOW: [
                MessageHandler(
                    Filters.regex(f'🍃 Lifetime|{mc.season_icon} Season'),
                    get_time_window
                ),
            ],
            SEND_RESULT: [
                MessageHandler(
                    Filters.regex(
                        '🔢 Everything|1️⃣ Solo|2️⃣ Duo|3️⃣ Trio|4️⃣ Squad|🔐 Limited modes'
                    ),
                    send_result
                ),
            ]
        },
        fallbacks=[MessageHandler(Filters.update, conversation_fallback)],
    )

    list_saved_players_handler = ConversationHandler(
        entry_points=[CommandHandler('list', list_saved_players)],
        states={
            SEND_RESULT_LIST: [
                MessageHandler(Filters.text, send_result_list),
            ]
        },
        fallbacks=[MessageHandler(Filters.update, conversation_fallback)],
    )

    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(search_handler)
    dispatcher.add_handler(replay_handler)
    dispatcher.add_handler(list_saved_players_handler)
    dispatcher.add_handler(credits_handler)
    dispatcher.add_handler(CallbackQueryHandler(save_player_button))
    dispatcher.add_handler(InlineQueryHandler(inlinequery))
    dispatcher.add_error_handler(error_handler)

    # Start the Bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
