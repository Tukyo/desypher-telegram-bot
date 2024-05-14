import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load environment variables from .env file
load_dotenv()

# Get the Telegram API token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')

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
    update.message.reply_text('Welcome to deSypher! This is a mini-game where you can test your skills in solving puzzles. The minigame is currently under development, check back soon!')

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
        'Website: https://desypher.net/\n'
    )

def sypher(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'SYPHER is the native token of deSypher. It is used to play the game, and can be earned by playing the game.\n'
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
    
    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
