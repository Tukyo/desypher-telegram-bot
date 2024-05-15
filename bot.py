import os
import time
import json
import random
from dotenv import load_dotenv
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler, JobQueue
from anti_spam import AntiSpam
from verify_user import handle_new_user, button_callback
from verification import handle_start_verification, handle_verification_button

# Load environment variables from .env file
load_dotenv()

# Get the Telegram API token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')

anti_spam = AntiSpam(rate_limit=5, time_window=10)

#region Slash Commands
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! I am the deSypher Bot. For a list of commands, please use /help.')

def help(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Here are the commands you can use:\n'
        '\n'
        '/start: This starts the bot, and sends a welcome message.\n'
        '/help: This is where you are now, you can see a list of commands here.\n'
        '/play: Start a mini-game of deSypher within Telegram. Have fun!\n'
        '/tukyo: This will provide information about the developer of this bot, and deSypher.\n'
        '/tukyogames: This will provide information about Tukyo Games and our projects.\n'
        '/deSypher: This will direct you to the main game, you can play it using SYPHER tokens!\n'
        '/sypher: This command will provide you with information about the SYPHER token.\n'
    )

def play(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Click Here to Start a Game!", callback_data='playGame')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('The game has started! Please guess a five letter word.', reply_markup=reply_markup)
    context.chat_data['game'] = {
        'word': fetch_random_word(),
        'guesses': 0,
        'status': 'playing',
        'history': []
    }

def handle_play_game(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data == 'playGame':
        context.bot.send_message(chat_id=query.message.chat_id, text='Please send your guess.')

def handle_guess(update: Update, context: CallbackContext) -> None:
    # Check if there is an active game
    if 'game' not in context.chat_data or context.chat_data['game']['status'] != 'playing':
        update.message.reply_text('No active game found. Please start a new game using /play.')
        return

    # Retrieve the guess from the message
    guess = update.message.text.lower().strip()
    # Validate the guess
    if len(guess) != 5 or not guess.isalpha():
        update.message.reply_text('Please ensure your guess is a five-letter word.')
        return

    # Access the game data stored in the chat context
    game_data = context.chat_data['game']
    # Process the guess if there are remaining attempts
    if game_data['guesses'] < 4:
        result = evaluate_guess(guess, game_data['word'])
        game_data['history'].append(result)
        game_data['guesses'] += 1

        message = 'The game has started! Please guess a five letter word.\n'
        message += '\n'.join(game_data['history'])

        # Check if the game is won or if all guesses are used
        if guess == game_data['word']:
            message = 'Congratulations! You won! 🎉 The word was ' + game_data['word']
            game_data['status'] = 'ended'
        elif game_data['guesses'] == 4:
            message = 'Game over! You\'ve used all your guesses. The correct word was ' + game_data['word']
            game_data['status'] = 'ended'

        update.message.reply_text(message)
    else:
        update.message.reply_text('Game over! No more guesses allowed.')



def evaluate_guess(guess, word):
    result = ''
    for i, letter in enumerate(guess):
        if letter == word[i]:
            result += '🟩'
        elif letter in word:
            result += '🟨'
        else:
            result += '🟥'
    return result

def fetch_random_word() -> str:
    with open('words.json', 'r') as file:
        data = json.load(file)
        words = data['words']
        return random.choice(words)

def tukyo(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Tukyo is the developer of this bot, deSypher and other projects. There are many impersonators, the only real Tukyo on telegram is @tukyowave.\n'
        '\n'
        '| Socials |\n'
        'Website: https://www.tukyo.org/\n'
        'Twitter/X: https://twitter.com/TUKYOWAVE\n'
        'Instagram: https://www.instagram.com/tukyowave/\n'
        'Medium: https://tukyo.medium.com/\n'
        'Spotify: https://sptfy.com/QGbt\n'
        'Bandcamp: https://tukyo.bandcamp.com/\n'
        'Github: https://github.com/tukyo\n'
    )

def tukyogames(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Tukyo Games is a game development studio that is focused on bringing innovative blockchain technology to captivating and new game ideas. We use blockchain technology, without hindering the gaming experience.\n'
        '\n'
        'Website: https://tukyogames.com/ (Coming Soon)\n'
        '\n'
        '| Projects |\n'
        'deSypher: https://desypher.net/\n'
        'Super G.I.M.P. Girl: https://superhobogimpgirl.com/\n'
        'Profectio: https://www.tukyowave.com/projects/profectio\n'
    )

def deSypher(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'deSypher is an Onchain puzzle game that can be played on Base. It is a game that requires SYPHER to play. The goal of the game is to guess the correct word in four attempts. Guess the correct word, or go broke!\n'
        '\n'
        'Website: https://desypher.net/\n'
    )

def sypher(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'SYPHER is the native token of deSypher. It is used to play the game, and can be earned by playing the game.\n'
        '\n'
        'Get SYPHER: [Uniswap](https://app.uniswap.org/#/swap?outputCurrency=0x21b9D428EB20FA075A29d51813E57BAb85406620)\n'
        'BaseScan: [Link](https://basescan.org/token/0x21b9d428eb20fa075a29d51813e57bab85406620)\n'
        'Contract Address: 0x21b9D428EB20FA075A29d51813E57BAb85406620\n'
        'Total Supply: 1,000,000\n'
        'Blockchain: Base\n'
        'Liquidity: Uniswap\n'
        'Ticker: SYPHER\n',
        parse_mode='Markdown',
        disable_web_page_preview=True
    )

def ca(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        '0x21b9D428EB20FA075A29d51813E57BAb85406620\n'
    )

def whitepaper(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
    'Whitepaper: https://desypher.net/whitepaper.html\n'
    )
#endregion Slash Commands

#region Admin Controls
def unmute_user(context: CallbackContext) -> None:
    job = context.job
    context.bot.restrict_chat_member(
        chat_id=job.context['chat_id'],
        user_id=job.context['user_id'],
        permissions=ChatPermissions(can_send_messages=True)
    )

def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id
    username = update.message.from_user.username or update.message.from_user.first_name

    if anti_spam.is_spam(user_id):
        mute_time = anti_spam.mute_time  # Get the mute time from AntiSpam class
        update.message.reply_text(f'{username}, you are spamming. You have been muted for {mute_time} seconds.')

        # Mute the user for the mute time
        until_date = int(time.time() + mute_time)
        context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )

        # Schedule job to unmute the user
        job_queue = context.job_queue
        job_queue.run_once(unmute_user, mute_time, context={'chat_id': chat_id, 'user_id': user_id})
#endregion Admin Controls

def main() -> None:
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Register the command handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("play", play))
    dispatcher.add_handler(CommandHandler("tukyo", tukyo))
    dispatcher.add_handler(CommandHandler("tukyogames", tukyogames))
    dispatcher.add_handler(CommandHandler("desypher", deSypher))
    dispatcher.add_handler(CommandHandler("sypher", sypher))
    dispatcher.add_handler(CommandHandler("contract", ca))
    dispatcher.add_handler(CommandHandler("ca", ca))
    dispatcher.add_handler(CommandHandler("tokenomics", sypher))

    # Register the message handler for anti-spam
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Register the message handler for new users
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, handle_new_user))

    # Register the callback query handler for button clicks
    dispatcher.add_handler(CallbackQueryHandler(button_callback, pattern='^verify$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_start_verification, pattern='start_verification'))
    dispatcher.add_handler(CallbackQueryHandler(handle_verification_button, pattern=r'verify_letter_[A-Z]'))
    dispatcher.add_handler(CallbackQueryHandler(handle_play_game, pattern='^playGame$'))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_guess))
    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()