import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Load environment variables from .env file
load_dotenv()

# Get the Telegram API token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')

def welcome(update: Update, context: CallbackContext) -> None:
    # Message content
    welcome_message = (
        "Welcome to Tukyo Games!\n\n"
        "Check out the links below.\n\n"
        "* Admins will NEVER DM YOU FIRST! *\n\n"
        "| deSypher\n"
        "🌐 · https://desypher.net/\n\n"
        "| TUKYO\n"
        "🌐 · https://tukyowave.com/\n"
        "🐦 · https://twitter.com/tukyowave/\n"
        "✉️ · @tukyowave\n\n"
        "| Profectio\n"
        "🌐 · https://www.tukyowave.com/profectio/\n"
        "🖼 · https://opensea.io/collection/profectio\n"
    )

    # Inline button
    keyboard = [[InlineKeyboardButton("Click Here to Verify", callback_data='verify')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send the welcome message
    for member in update.message.new_chat_members:
        context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_message, reply_markup=reply_markup)

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Verification button clicked! (functionality to be added later)")
