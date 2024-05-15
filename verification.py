import os
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Load environment variables from .env file
load_dotenv()

# Get the verification letters from environment variables
VERIFICATION_LETTERS = os.getenv('VERIFICATION_LETTERS')

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

def handle_start_verification(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()

    # Initialize user verification progress
    user_verification_progress[user_id] = {
        'progress': [],
        'verification_message_id': query.message.message_id
    }

    verification_question = "Who is the lead developer at Tukyo Games?"
    reply_markup = generate_verification_buttons()

    print("Verification question:", verification_question)  # Debug log
    print("Reply markup:", reply_markup)  # Debug log

    # Delete the initial verification prompt
    context.bot.delete_message(chat_id=user_id, message_id=user_verification_progress[user_id]['verification_message_id'])

    # Send the verification question with buttons
    message = query.message.reply_text(text=verification_question, reply_markup=reply_markup)
    user_verification_progress[user_id]['verification_message_id'] = message.message_id

def handle_verification_button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    letter = query.data.split('_')[2]  # Get the letter from callback_data
    query.answer()

    # Update user verification progress
    if user_id in user_verification_progress:
        user_verification_progress[user_id]['progress'].append(letter)
        print(f"User {user_id} pressed: {letter}")
        print(f"Current progress: {user_verification_progress[user_id]['progress']}")

        # Only check the sequence after the fifth button press
        if len(user_verification_progress[user_id]['progress']) == len(VERIFICATION_LETTERS):
            if user_verification_progress[user_id]['progress'] == list(VERIFICATION_LETTERS):
                query.message.reply_text("Verification successful, you may now return to chat!")
                # Delete the verification question and buttons
                context.bot.delete_message(chat_id=user_id, message_id=user_verification_progress[user_id]['verification_message_id'])
            else:
                query.message.reply_text("Verification failed. Please try again.")
                # Delete the verification question and buttons, and resend the verification question
                context.bot.delete_message(chat_id=user_id, message_id=user_verification_progress[user_id]['verification_message_id'])
                handle_start_verification(update, context)
            # Reset progress after verification attempt
            user_verification_progress.pop(user_id)
    else:
        query.message.reply_text("Verification failed. Please try again.")
