import os
import time
import json
import random
from dotenv import load_dotenv
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler, JobQueue
from collections import defaultdict
from collections import deque

# Load environment variables from .env file
load_dotenv()

# Get the Telegram API token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')
VERIFICATION_LETTERS = os.getenv('VERIFICATION_LETTERS')
CHAT_ID = os.getenv('CHAT_ID')

#region Classes
class AntiSpam:
    def __init__(self, rate_limit=5, time_window=10, mute_time=60):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.mute_time = mute_time
        self.user_messages = defaultdict(list)
        self.blocked_users = defaultdict(lambda: 0)

    def is_spam(self, user_id):
        current_time = time.time()
        if current_time < self.blocked_users[user_id]:
            return True
        self.user_messages[user_id] = [msg_time for msg_time in self.user_messages[user_id] if current_time - msg_time < self.time_window]
        self.user_messages[user_id].append(current_time)
        if len(self.user_messages[user_id]) > self.rate_limit:
            self.blocked_users[user_id] = current_time + self.mute_time
            return True
        return False

    def time_to_wait(self, user_id):
        current_time = time.time()
        if current_time < self.blocked_users[user_id]:
            return int(self.blocked_users[user_id] - current_time)
        return 0

class AntiRaid:
    def __init__(self, user_amount, time_out, anti_raid_time):
        self.user_amount = user_amount
        self.time_out = time_out
        self.anti_raid_time = anti_raid_time
        self.join_times = deque()
        self.anti_raid_end_time = 0
        print(f"Initialized AntiRaid with user_amount={user_amount}, time_out={time_out}, anti_raid_time={anti_raid_time}")

    def is_raid(self):
        current_time = time.time()
        if current_time < self.anti_raid_end_time:
            return True

        self.join_times.append(current_time)
        print(f"User joined at time {current_time}. Join times: {list(self.join_times)}")
        while self.join_times and current_time - self.join_times[0] > self.time_out:
            self.join_times.popleft()

        if len(self.join_times) >= self.user_amount:
            self.anti_raid_end_time = current_time + self.anti_raid_time
            self.join_times.clear()
            print(f"Raid detected. Setting anti-raid end time to {self.anti_raid_end_time}. Cleared join times.")
            return True

        print(f"No raid detected. Current join count: {len(self.join_times)}")
        return False

    def time_to_wait(self):
        current_time = time.time()
        if current_time < self.anti_raid_end_time:
            return int(self.anti_raid_end_time - current_time)
        return 0
#endregion Classes

anti_spam = AntiSpam(rate_limit=5, time_window=10)
anti_raid = AntiRaid(user_amount=4, time_out=20, anti_raid_time=30)

# Initialize a dictionary to keep track of user verification progress
user_verification_progress = {}

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

#region Play Game
def play(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Click Here to Start a Game!", callback_data='playGame')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Welcome to deSypher! Click the button below to start a game!', reply_markup=reply_markup)

def handle_play_game(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data == 'playGame':
        word = fetch_random_word()
        # Store the chosen word in the user's context to use later in the game logic
        context.user_data['chosen_word'] = word
        # Dynamically generate the game layout
        num_rows = 4
        row_template = "⬛⬛⬛⬛⬛"
        game_layout = "\n".join([row_template for _ in range(num_rows)])
        # Update the message with the game layout
        game_message = query.edit_message_text(text=f"Please guess a five letter word!\n{game_layout}")
        # Store the message ID in the user's context to update it later
        context.user_data['game_message_id'] = game_message.message_id
        # Store the chat ID to ensure it's the specific user
        context.user_data['chat_id'] = query.message.chat_id

def handle_guess(update: Update, context: CallbackContext) -> None:
    user_guess = update.message.text.lower()
    chosen_word = context.user_data.get('chosen_word')

    if not chosen_word:
        update.message.reply_text("Please start a game first by using /play.")
        return

    if len(user_guess) != 5:
        update.message.reply_text("Please guess a five-letter word!")
        return

    # Check the guess and build the game layout
    def get_game_layout(guesses, chosen_word):
        layout = []
        for guess in guesses:
            row = ""
            for i, char in enumerate(guess):
                if char == chosen_word[i]:
                    row += "🟩"  # Correct letter in the correct position
                elif char in chosen_word:
                    row += "🟨"  # Correct letter in the wrong position
                else:
                    row += "🟥"  # Incorrect letter
            layout.append(row)
        return "\n".join(layout)

    if 'guesses' not in context.user_data:
        context.user_data['guesses'] = []

    context.user_data['guesses'].append(user_guess)

    # Update the game layout
    game_layout = get_game_layout(context.user_data['guesses'], chosen_word)
    chat_id = context.user_data.get('chat_id')
    message_id = context.user_data.get('game_message_id')
    if chat_id and message_id:
        context.bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                      text=f"Please guess a five letter word!\n{game_layout}")

    # Check if the user has guessed the word correctly
    if user_guess == chosen_word:
        update.message.reply_text("Congratulations! You've guessed the word correctly!")
        # Reset the game state
        context.user_data.clear()
    elif len(context.user_data['guesses']) >= 4:
        update.message.reply_text(f"Game over! The correct word was: {chosen_word}")
        context.user_data.clear()

def update_game_layout(update: Update, context: CallbackContext) -> None:
    chat_id = context.user_data.get('chat_id')
    message_id = context.user_data.get('game_message_id')
    if chat_id and message_id:
        # Update the game layout for the specific user
        new_layout = "New game layout based on user input"
        context.bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=new_layout)

def fetch_random_word() -> str:
    with open('words.json', 'r') as file:
        data = json.load(file)
        words = data['words']
        return random.choice(words)
#endregion Play Game

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

def handle_new_user(update: Update, context: CallbackContext) -> None:
    if anti_raid.is_raid():
        update.message.reply_text(f'Anti-raid triggered! Please wait {anti_raid.time_to_wait()} seconds before new users can join.')
        return
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
        job_queue.run_once(kick_user, 60, context={'chat_id': chat_id, 'user_id': user_id}, name=str(user_id))

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
                    chat_id=CHAT_ID,
                    user_id=user_id,
                    permissions=ChatPermissions(can_send_messages=True)
                )
                current_jobs = context.job_queue.get_jobs_by_name(str(user_id))
                for job in current_jobs:
                    job.schedule_removal()
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
    query.answer()

    # Send a message to the user's DM to start the verification process
    start_verification_dm(user_id, context)
    
    # Optionally, you can edit the original message to indicate the button was clicked
    query.edit_message_text(text="A verification message has been sent to your DMs. Please check your messages.")

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

def handle_anti_raid(update: Update, context: CallbackContext) -> None:
    if anti_raid.is_raid():
        update.message.reply_text(f'Anti-raid triggered! Please wait {anti_raid.time_to_wait()} seconds before new users can join.')
        
        # Get the user_id of the user that just joined
        user_id = update.message.new_chat_members[0].id

        # Kick the user that just joined
        context.bot.kick_chat_member(chat_id=update.message.chat_id, user_id=user_id)
        return
    handle_new_user(update, context)
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

    # Register the message handler for guesses
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_guess))
    
    # Register the message handler for anti-spam
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Register the message handler for new users
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, handle_anti_raid))

    # Register the callback query handler for button clicks
    dispatcher.add_handler(CallbackQueryHandler(button_callback, pattern='^verify$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_start_verification, pattern='start_verification'))
    dispatcher.add_handler(CallbackQueryHandler(handle_verification_button, pattern=r'verify_letter_[A-Z]'))
    dispatcher.add_handler(CallbackQueryHandler(handle_play_game, pattern='^playGame$'))
    
    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()