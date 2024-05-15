import os
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatPermissions
from telegram.ext import CallbackContext, JobQueue

# Load environment variables from .env file
load_dotenv()

# Get the verification letters and Telegram API token from environment variables
VERIFICATION_LETTERS = os.getenv('VERIFICATION_LETTERS')
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')

# Initialize a dictionary to keep track of user verification progress
user_verification_progress = {}

def start_verification_dm(user_id: int, context: CallbackContext) -> None:
    verification_message = "Welcome to Tukyo Games! Please click the button to begin verification."
    keyboard = [[InlineKeyboardButton("Start Verification", callback_data='start_verification')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    message = context.bot.send_message(chat_id=user_id, text=verification_message, reply_markup=reply_markup)
    return message.message_id

def generate_verification_buttons() -> InlineKeyboardMarkup:
    all_letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    required_letters = list(VERIFICATION_LETTERS)
    
    # Ensure all required letters are included
    for letter in required_letters:
        if letter in all_letters:
            all_letters.remove(letter)
    
    # Shuffle the remaining letters
    random.shuffle(all_letters)
    
    # Randomly select 11 letters from the shuffled list
    selected_random_letters = all_letters[:11]
    
    # Combine required letters with the random letters
    final_letters = required_letters + selected_random_letters
    
    # Shuffle the final list of 16 letters
    random.shuffle(final_letters)
    
    buttons = []
    row = []
    for i, letter in enumerate(final_letters):
        row.append(InlineKeyboardButton(letter, callback_data=f'verify_letter_{letter}'))
        if (i + 1) % 4 == 0:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons)

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

        keyboard = [[InlineKeyboardButton("Click Here to Verify", callback_data='verify')]]
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
    chat_id = query.data.split('_')[1]
    query.answer()

    # Store the main chat ID in the user verification progress
    user_verification_progress[user_id] = {
        'main_chat_id': chat_id
    }

    # Send a message to the user's DM to start the verification process
    start_verification_dm(user_id, context)
    
    # Optionally, you can edit the original message to indicate the button was clicked
    query.edit_message_text(text="A verification message has been sent to your DMs. Please check your messages.")


def handle_start_verification(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()

    # Initialize user verification progress
    user_verification_progress[user_id] = {
        'progress': [],
        'main_message_id': query.message.message_id,
        'chat_id': query.message.chat_id,
        'verification_message_id': query.message.message_id
    }

    verification_question = "Who is the lead developer at Tukyo Games?"
    reply_markup = generate_verification_buttons()

    # Edit the initial verification prompt
    context.bot.edit_message_text(
        chat_id=user_id,
        message_id=user_verification_progress[user_id]['verification_message_id'],
        text=verification_question,
        reply_markup=reply_markup
    )

def handle_verification_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    letter = query.data.split('_')[2]  # Get the letter from callback_data
    query.answer()

    # Update user verification progress
    if user_id in user_verification_progress:
        user_verification_progress[user_id]['progress'].append(letter)

        # Only check the sequence after the fifth button press
        if len(user_verification_progress[user_id]['progress']) == len(VERIFICATION_LETTERS):
            if user_verification_progress[user_id]['progress'] == list(VERIFICATION_LETTERS):
                context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=user_verification_progress[user_id]['verification_message_id'],
                    text="Verification successful, you may now return to chat!"
                )
                # Unmute the user in the main chat
                context.bot.restrict_chat_member(
                    chat_id=user_verification_progress[user_id]['main_chat_id'], 
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=True)
                )
            else:
                context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=user_verification_progress[user_id]['verification_message_id'],
                    text="Verification failed. Please try again.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Start Verification", callback_data='start_verification')]])
                )
            # Reset progress after verification attempt
            user_verification_progress.pop(user_id)
    else:
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=user_verification_progress[user_id]['verification_message_id'],
            text="Verification failed. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Start Verification", callback_data='start_verification')]])
        )