import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from verification import start_verification_dm

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
    user_id = query.from_user.id
    query.answer()

    # Send a message to the user's DM to start the verification process
    start_verification_dm(user_id, context)
    
    # Optionally, you can edit the original message to indicate the button was clicked
    query.edit_message_text(text="A verification message has been sent to your DMs. Please check your messages.")
