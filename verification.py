import os
import random
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Load environment variables from .env file
load_dotenv()

# Get the verification letters from environment variables
VERIFICATION_LETTERS = os.getenv('VERIFICATION_LETTERS')

def start_verification_dm(user_id: int, context: CallbackContext) -> None:
    verification_message = "Welcome to Tukyo Games! Please click the button to begin verification."
    keyboard = [[InlineKeyboardButton("Start Verification", callback_data='start_verification')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    context.bot.send_message(chat_id=user_id, text=verification_message, reply_markup=reply_markup)

def generate_verification_buttons() -> InlineKeyboardMarkup:
    letters = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    required_letters = list(VERIFICATION_LETTERS)
    random.shuffle(letters)
    
    for letter in required_letters:
        if letter not in letters:
            letters[random.randint(0, len(letters) - 1)] = letter
    
    buttons = []
    row = []
    for i, letter in enumerate(letters[:16]):
        row.append(InlineKeyboardButton(letter, callback_data=f'verify_{letter}'))
        if (i + 1) % 4 == 0:
            buttons.append(row)
            row = []

    return InlineKeyboardMarkup(buttons)

def handle_start_verification(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()

    verification_question = "Who is the lead developer at Tukyo Games?"
    reply_markup = generate_verification_buttons()

    query.edit_message_text(text=verification_question, reply_markup=reply_markup)
