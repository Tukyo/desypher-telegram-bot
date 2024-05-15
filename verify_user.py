import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import CallbackContext, JobQueue
from verification import start_verification_dm
from shared import user_verification_progress  # Import the shared dictionary

# Load environment variables from .env file
load_dotenv()

# Get the Telegram API token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')

def handle_new_user(update: Update, context: CallbackContext) -> None:
    for member in update.message.new_chat_members:
        user_id = member.id
        chat_id = update.message.chat.id

        # Mute the new user
        context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=False)
        )

        # Send the welcome message with the verification button
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

        keyboard = [[InlineKeyboardButton("Click Here to Verify", callback_data=f'verify_{chat_id}')]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        context.bot.send_message(chat_id=chat_id, text=welcome_message, reply_markup=reply_markup)

        # Start a verification timeout job
        job_queue = context.job_queue
        job_queue.run_once(kick_user, 600, context={'chat_id': chat_id, 'user_id': user_id})

def kick_user(context: CallbackContext) -> None:
    job = context.job
    context.bot.kick_chat_member(
        chat_id=job.context['chat_id'],
        user_id=job.context['user_id']
    )
    context.bot.send_message(
        chat_id=job.context['chat_id'],
        text=f"User {job.context['user_id']} has been kicked for not verifying in time."
    )

def button_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.data.split('_')[1]  # Extract chat_id from callback_data
    query.answer()

    # Store the main chat ID in the user verification progress
    user_verification_progress[user_id] = {
        'main_chat_id': chat_id
    }

    # Send a message to the user's DM to start the verification process
    start_verification_dm(user_id, context)
    
    # Optionally, you can edit the original message to indicate the button was clicked
    query.edit_message_text(text="A verification message has been sent to your DMs. Please check your messages.")
