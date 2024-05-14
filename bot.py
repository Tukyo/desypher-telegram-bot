import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Load environment variables from .env file
load_dotenv()

# Get the Telegram API token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! I am your bot. For a list of commands, please use /help.')

def main() -> None:
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_TOKEN)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    # Register the /start command handler
    dispatcher.add_handler(CommandHandler("start", start))
    
    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()
