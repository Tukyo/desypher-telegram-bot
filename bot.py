import os
import time
import json
import random
import requests
import telegram
import pandas as pd
import mplfinance as mpf
from web3 import Web3
from dotenv import load_dotenv
from collections import deque, defaultdict
from telegram import Update, ChatPermissions, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters, CallbackQueryHandler, JobQueue

#
## This bot was developed by Tukyo Games for the deSypher project.
## https://desypher.net/
#
## Commands
### /start - Start the bot
### /help - Get a list of commands
### /play - Start a mini-game of deSypher within Telegram
### /endgame - End your current game
### /tukyo - Information about the developer of this bot and deSypher
### /tukyogames - Information about Tukyo Games and our projects
### /deSypher - Direct link to the main game, play it using SYPHER tokens
### /sypher - Information about the SYPHER token
### /contract /ca - Contract address for the SYPHER token
### /tokenomics - Information about the SYPHER token
### /website - Link to the deSypher website
#
## Ethereum Commands
### /price - Get the price of the SYPHER token in USD
### /chart - Links to the token chart on various platforms
#
## Admin Commands
### /cleargames - Clear all active games in the chat
### /antiraid - Manage the anti-raid system
#### /antiraid end /anti-raid [user_amount] [time_out] [anti_raid_time]
### /mute /unmute - Reply to a message with this command to toggle mute for a user
### /kick - Reply to a message with this command to kick a user from the chat
#

with open('config.json') as f:
    config = json.load(f)

# Load environment variables from .env file
load_dotenv()

# Get the Telegram API token from environment variables
TELEGRAM_TOKEN = os.getenv('BOT_API_TOKEN')
VERIFICATION_LETTERS = os.getenv('VERIFICATION_LETTERS')
CHAT_ID = os.getenv('CHAT_ID')
BASE_ENDPOINT = os.getenv('ENDPOINT')
BASESCAN_API_KEY = os.getenv('BASESCAN_API')

web3 = Web3(Web3.HTTPProvider(BASE_ENDPOINT))
contract_address = config['contractAddress']
abi = config['abi']

if web3.is_connected():
    network_id = web3.net.version
    print(f"Connected to Ethereum node on network {network_id}")
else:
    print("Failed to connect")

# Create a contract instance
contract = web3.eth.contract(address=contract_address, abi=abi)

#region Classes
class AntiSpam:
    def __init__(self, rate_limit, time_window, mute_time):
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.mute_time = mute_time
        self.user_messages = defaultdict(list)
        self.blocked_users = defaultdict(lambda: 0)
        print(f"Initialized AntiSpam with rate_limit={rate_limit}, time_window={time_window}, mute_time={mute_time}")

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

anti_spam = AntiSpam(rate_limit=5, time_window=10, mute_time=60)
anti_raid = AntiRaid(user_amount=20, time_out=30, anti_raid_time=180)

RATE_LIMIT = 100  # Maximum number of allowed commands
TIME_PERIOD = 60  # Time period in seconds
last_check_time = time.time()
command_count = 0

user_verification_progress = {}

#region Main Slash Commands
def start(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
        update.message.reply_text('Hello! I am the deSypher Bot. For a list of commands, please use /help.')
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def help(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
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
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

#region Play Game
def play(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Click Here to Start a Game!", callback_data='startGame')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    base_dir = os.path.dirname(__file__)
    photo_path = os.path.join(base_dir, 'assets', 'banner.gif')
    
    with open(photo_path, 'rb') as photo:
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption='Welcome to deSypher! Click the button below to start a game!', reply_markup=reply_markup)

def end_game(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    key = f"{chat_id}_{user_id}"  # Unique key for each user-chat combination

    # Check if there's an ongoing game for this user in this chat
    if key in context.chat_data:
        # Delete the game message
        if 'game_message_id' in context.chat_data[key]:
            context.bot.delete_message(chat_id=chat_id, message_id=context.chat_data[key]['game_message_id'])

        # Clear the game data
        del context.chat_data[key]
        update.message.reply_text("Your game has been deleted.")
    else:
        update.message.reply_text("You don't have an ongoing game.")

def handle_start_game(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data == 'startGame':
        user_id = query.from_user.id
        first_name = query.from_user.first_name  # Get the user's first name
        chat_id = query.message.chat_id
        key = f"{chat_id}_{user_id}"

        # Check if the user already has an ongoing game
        if key in context.chat_data:
            # Delete the old message
            context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)
            # Send a new message
            context.bot.send_message(chat_id=chat_id, text="You already have an active game. Please use the command */endgame* to end your previous game before starting a new one!", parse_mode='Markdown')
            return

        word = fetch_random_word()
        print(f"Chosen word: {word} for key: {key}")

        # Initialize the game state for this user in this chat
        if key not in context.chat_data:
            context.chat_data[key] = {
                'chosen_word': word,
                'guesses': [],
                'game_message_id': None,
                'chat_id': chat_id,
                'player_name': first_name
            }

        num_rows = 4
        row_template = "⬛⬛⬛⬛⬛"
        game_layout = "\n".join([row_template for _ in range(num_rows)])
        
        # Delete the old message
        context.bot.delete_message(chat_id=chat_id, message_id=query.message.message_id)

        # Send a new message with the game layout and store the message ID
        game_message = context.bot.send_message(chat_id=chat_id, text=f"*{first_name}'s Game*\nPlease guess a five letter word!\n\n{game_layout}", parse_mode='Markdown')
        context.chat_data[key]['game_message_id'] = game_message.message_id
        
        print(f"Game started for {first_name} in {chat_id} with message ID {game_message.message_id}")

def handle_guess(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    key = f"{chat_id}_{user_id}"
    player_name = context.chat_data[key].get('player_name', 'Player')

    # print(f"User {user_id} in chat {chat_id} guessed: {update.message.text}")

    # Check if there's an ongoing game for this user in this chat
    if key not in context.chat_data or 'chosen_word' not in context.chat_data[key]:
        # print(f"No active game found for key: {key}")
        return

    user_guess = update.message.text.lower()
    chosen_word = context.chat_data[key].get('chosen_word')

    # Check if the guess is not 5 letters and the user has an active game
    if len(user_guess) != 5 or not user_guess.isalpha():
        print(f"Invalid guess length: {len(user_guess)}")
        update.message.reply_text("Please guess a five letter word containing only letters!")
        return

    if 'guesses' not in context.chat_data[key]:
        context.chat_data[key]['guesses'] = []
        print(f"Initialized guesses list for key: {key}")

    context.chat_data[key]['guesses'].append(user_guess)
    print(f"Updated guesses list: {context.chat_data[key]['guesses']}")

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
            layout.append(row + " - " + guess)

        while len(layout) < 4:
            layout.append("⬛⬛⬛⬛⬛")
        
        return "\n".join(layout)

    # Delete the previous game message
    if 'game_message_id' in context.chat_data[key]:
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=context.chat_data[key]['game_message_id'])
        except telegram.error.BadRequest:
            print("Message to delete not found")

    # Update the game layout
    game_layout = get_game_layout(context.chat_data[key]['guesses'], chosen_word)

    # Check if it's not the 4th guess and the user hasn't guessed the word correctly before sending the game message
    if len(context.chat_data[key]['guesses']) < 4 and user_guess != chosen_word:
        game_message = context.bot.send_message(chat_id=chat_id, text=f"*{player_name}'s Game*\nPlease guess a five letter word!\n\n{game_layout}", parse_mode='Markdown')
    
        # Store the new message ID
        context.chat_data[key]['game_message_id'] = game_message.message_id

    # Check if the user has guessed the word correctly
    if user_guess == chosen_word:
        # Delete the previous game message
        if 'game_message_id' in context.chat_data[key]:
            try:
                context.bot.delete_message(chat_id=chat_id, message_id=context.chat_data[key]['game_message_id'])
            except telegram.error.BadRequest:
                print("Message to delete not found")

        # Update the game layout
        game_layout = get_game_layout(context.chat_data[key]['guesses'], chosen_word)
        game_message = context.bot.send_message(chat_id=chat_id, text=f"*{player_name}'s Final Results:*\n\n{game_layout}\n\nCongratulations! You've guessed the word correctly!\n\nIf you enjoyed this, you can play the game with SYPHER tokens on the [*website*](https://desypher.net/).", parse_mode='Markdown')
        print("User guessed the word correctly. Clearing game data.")
        del context.chat_data[key]
    elif len(context.chat_data[key]['guesses']) >= 4:
        # Delete the previous game message
        if 'game_message_id' in context.chat_data[key]:
            try:
                context.bot.delete_message(chat_id=chat_id, message_id=context.chat_data[key]['game_message_id'])
            except telegram.error.BadRequest:
                print("Message to delete not found")

        # Update the game layout
        game_layout = get_game_layout(context.chat_data[key]['guesses'], chosen_word)
        game_message = context.bot.send_message(chat_id=chat_id, text=f"*{player_name}'s Final Results:*\n\n{game_layout}\n\nGame over! The correct word was: {chosen_word}\n\nTry again on the [*website*](https://desypher.net/), you'll probably have better luck if you play with SPYHER tokens.", parse_mode='Markdown')

        print(f"Game over. User failed to guess the word {chosen_word}. Clearing game data.")
        del context.chat_data[key]

def fetch_random_word() -> str:
    with open('words.json', 'r') as file:
        data = json.load(file)
        words = data['words']
        return random.choice(words)
#endregion Play Game

def tukyo(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
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
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def tukyogames(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
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
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def deSypher(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
        update.message.reply_text(
            'deSypher is an Onchain puzzle game that can be played on Base. It is a game that requires SYPHER to play. The goal of the game is to guess the correct word in four attempts. Guess the correct word, or go broke!\n'
            '\n'
            'Website: https://desypher.net/\n'
        )
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def sypher(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
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
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def ca(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
        update.message.reply_text(
            '0x21b9D428EB20FA075A29d51813E57BAb85406620\n'
        )
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def whitepaper(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
        update.message.reply_text(
        'Whitepaper: https://desypher.net/whitepaper.html\n'
        )
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def website(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
        update.message.reply_text(
            'https://desypher.net/\n'
        )
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')
#endregion Main Slash Commands

#region Ethereum Logic
def get_token_price_in_weth(contract_address):
    apiUrl = f"https://api.dexscreener.com/latest/dex/tokens/{contract_address}"
    try:
        response = requests.get(apiUrl)
        response.raise_for_status()
        data = response.json()
        
        if data['pairs'] and len(data['pairs']) > 0:
            # Find the pair with WETH as the quote token
            weth_pair = next((pair for pair in data['pairs'] if pair['quoteToken']['symbol'] == 'WETH'), None)
            
            if weth_pair:
                price_in_weth = weth_pair['priceNative']
                return price_in_weth
            else:
                print("No WETH pair found for this token.")
                return None
        else:
            print("No pairs found for this token.")
            return None
    except requests.RequestException as e:
        print(f"Error fetching token price from DexScreener: {e}")
        return None
    
def get_weth_price_in_fiat(currency):
    apiUrl = f"https://api.coingecko.com/api/v3/simple/price?ids=ethereum&vs_currencies={currency}"
    try:
        response = requests.get(apiUrl)
        response.raise_for_status()  # This will raise an exception for HTTP errors
        data = response.json()
        return data['ethereum'][currency]
    except requests.RequestException as e:
        print(f"Error fetching WETH price from CoinGecko: {e}")
        return None
    
def get_token_price_in_fiat(contract_address, currency):
    # Fetch price of token in WETH
    token_price_in_weth = get_token_price_in_weth(contract_address)
    if token_price_in_weth is None:
        print("Could not retrieve token price in WETH.")
        return None

    # Fetch price of WETH in the specified currency
    weth_price_in_fiat = get_weth_price_in_fiat(currency)
    if weth_price_in_fiat is None:
        print(f"Could not retrieve WETH price in {currency}.")
        return None

    # Calculate token price in the specified currency
    token_price_in_fiat = float(token_price_in_weth) * weth_price_in_fiat
    return token_price_in_fiat

def fetch_ohlcv_data():
    current_timestamp = int(time.time())  # Current time as Unix timestamp
    url = "https://api.geckoterminal.com/api/v2/networks/base/pools/0xB0fbaa5c7D28B33Ac18D9861D4909396c1B8029b/ohlcv/day"
    params = {
        'aggregate': '1h',
        'before_timestamp': current_timestamp,
        'limit': '100',
        'currency': 'usd'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()  # Process this data as needed
    else:
        print("Failed to fetch data:", response.status_code)
        return None

ohlcv_data = fetch_ohlcv_data()
# print(ohlcv_data)

def prepare_data_for_chart(ohlcv_data):
    # Create a list of dictionaries, one for each candlestick
    ohlcv_list = ohlcv_data['data']['attributes']['ohlcv_list']
    data = [{
        'Date': pd.to_datetime(item[0], unit='s'),  # Convert UNIX timestamp to datetime
        'Open': item[1],
        'High': item[2],
        'Low': item[3],
        'Close': item[4],
        'Volume': item[5]
    } for item in ohlcv_list]

    # Create DataFrame
    data_frame = pd.DataFrame(data)
    data_frame.set_index('Date', inplace=True)  # Set the datetime as the index
    return data_frame

# Assuming `ohlcv_data` is fetched from the function `fetch_ohlcv_data()`
data_frame = prepare_data_for_chart(ohlcv_data)
print(data_frame.head())  # Print first few rows to verify

def plot_candlestick_chart(data_frame):
    # Set the style and plot the chart
    mpf_style = mpf.make_mpf_style(base_mpf_style='charles', rc={'font.size': 8})
    save_path = '/tmp/candlestick_chart.png'  # Use /tmp directory to save the chart
    mpf.plot(data_frame, type='candle', style=mpf_style, volume=True, savefig=save_path)
    print(f"Chart saved to {save_path}")

#endregion Ethereum Logic

#region Ethereum Slash Commands
def price(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
        currency = context.args[0] if context.args else 'usd'
        currency = currency.lower()

        # Check if the provided currency is supported
        if currency not in ['usd', 'eur', 'jpy', 'gbp', 'aud', 'cad', 'mxn']:
            update.message.reply_text("Unsupported currency. Please use 'usd', 'eur'. 'jpy', 'gbp', 'aud', 'cad' or 'mxn'.")
            return

        # Fetch and format the token price in the specified currency
        token_price_in_fiat = get_token_price_in_fiat(contract_address, currency)
        if token_price_in_fiat is not None:
            formatted_price = format(token_price_in_fiat, '.4f')
            update.message.reply_text(f"SYPHER • {currency.upper()}: {formatted_price}")
        else:
            update.message.reply_text(f"Failed to retrieve the price of the token in {currency.upper()}.")
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')

def chart(update: Update, context: CallbackContext) -> None:
    if rate_limit_check():
        ohlcv_data = fetch_ohlcv_data()
        if ohlcv_data:
            data_frame = prepare_data_for_chart(ohlcv_data)
            plot_candlestick_chart(data_frame)
            update.message.reply_photo(photo=open('/tmp/candlestick_chart.png', 'rb'))
            update.message.reply_text(
                '[Dexscreener](https://dexscreener.com/base/0xb0fbaa5c7d28b33ac18d9861d4909396c1b8029b) • [Dextools](https://www.dextools.io/app/en/base/pair-explorer/0xb0fbaa5c7d28b33ac18d9861d4909396c1b8029b?t=1715831623074) • [CMC](https://coinmarketcap.com/dexscan/base/0xb0fbaa5c7d28b33ac18d9861d4909396c1b8029b/) • [CG](https://www.geckoterminal.com/base/pools/0xb0fbaa5c7d28b33ac18d9861d4909396c1b8029b?utm_source=coingecko)\n',
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        else:
            update.message.reply_text('Failed to fetch data or generate chart. Please try again later.')
    else:
        update.message.reply_text('Bot rate limit exceeded. Please try again later.')
#endregion Ethereum Slash Commands

#region User Verification
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

        if anti_raid.is_raid():
            update.message.reply_text(f'Anti-raid triggered! Please wait {anti_raid.time_to_wait()} seconds before new users can join.')
            
            # Get the user_id of the user that just joined
            user_id = update.message.new_chat_members[0].id

            # Kick the user that just joined
            context.bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
            return
        
        print("Allowing new user to join, antiraid is not active.")

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
#endregion User Verification

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

def rate_limit_check():
    global last_check_time, command_count
    current_time = time.time()

    # Reset count if time period has expired
    if current_time - last_check_time > TIME_PERIOD:
        command_count = 0
        last_check_time = current_time

    # Check if the bot is within the rate limit
    if command_count < RATE_LIMIT:
        command_count += 1
        return True
    else:
        return False
#endregion Admin Controls

#region Admin Slash Commands
def is_user_admin(update: Update, context: CallbackContext) -> bool:
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # Check if the user is an admin in this chat
    chat_admins = context.bot.get_chat_administrators(chat_id)
    user_is_admin = any(admin.user.id == user_id for admin in chat_admins)

    return user_is_admin

def cleargames(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if is_user_admin(update, context):
        keys_to_delete = [key for key in context.chat_data.keys() if key.startswith(f"{chat_id}_")]
        for key in keys_to_delete:
            del context.chat_data[key]
            print(f"Deleted key: {key}")
    
        update.message.reply_text("All active games have been cleared.")
    else:
        update.message.reply_text("You must be an admin to use this command.")
        print(f"User {update.effective_user.id} tried to clear games but is not an admin in chat {update.effective_chat.id}.")

def antiraid(update: Update, context: CallbackContext) -> None:
    args = context.args

    if is_user_admin(update, context):
        if not args:
            update.message.reply_text("Usage: /antiraid end or /antiraid [user_amount] [time_out] [anti_raid_time]")
            return

        command = args[0]
        if command == 'end':
            if anti_raid.is_raid():
                anti_raid.anti_raid_end_time = 0
                update.message.reply_text("Anti-raid timer ended. System reset to normal operation.")
                print("Anti-raid timer ended. System reset to normal operation.")
            else:
                update.message.reply_text("No active anti-raid to end.")
        else:
            try:
                user_amount = int(args[0])
                time_out = int(args[1])
                anti_raid_time = int(args[2])
                anti_raid.user_amount = user_amount
                anti_raid.time_out = time_out
                anti_raid.anti_raid_time = anti_raid_time
                update.message.reply_text(f"Anti-raid settings updated: user_amount={user_amount}, time_out={time_out}, anti_raid_time={anti_raid_time}")
                print(f"Updated AntiRaid settings to user_amount={user_amount}, time_out={time_out}, anti_raid_time={anti_raid_time}")
            except (IndexError, ValueError):
                update.message.reply_text("Invalid arguments. Usage: /antiraid [user_amount] [time_out] [anti_raid_time]")
    else:
        update.message.reply_text("You must be an admin to use this command.")
        print(f"User {update.effective_user.id} tried to use /antiraid but is not an admin in chat {update.effective_chat.id}.")

def toggle_mute(update: Update, context: CallbackContext, mute: bool) -> None:
    chat_id = update.effective_chat.id

    if is_user_admin(update, context):
        reply_to_message = update.message.reply_to_message
        if reply_to_message:
            user_id = reply_to_message.from_user.id
            username = reply_to_message.from_user.username or reply_to_message.from_user.first_name
        else:
            update.message.reply_text("Please reply to a message from the user you want to mute or unmute.")
            return

        context.bot.restrict_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            permissions=ChatPermissions(can_send_messages=not mute)
        )

        action = "muted" if mute else "unmuted"
        update.message.reply_text(f"User {username} has been {action}.")
    else:
        update.message.reply_text("You must be an admin to use this command.")

def mute(update: Update, context: CallbackContext) -> None:
    toggle_mute(update, context, True)

def unmute(update: Update, context: CallbackContext) -> None:
    toggle_mute(update, context, False)

def kick(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id

    if is_user_admin(update, context):
        reply_to_message = update.message.reply_to_message
        if reply_to_message:
            user_id = reply_to_message.from_user.id
            username = reply_to_message.from_user.username or reply_to_message.from_user.first_name
        else:
            update.message.reply_text("Please reply to a message from the user you want to kick.")
            return

        context.bot.kick_chat_member(chat_id=chat_id, user_id=user_id)
        update.message.reply_text(f"User {username} has been kicked.")
    else:
        update.message.reply_text("You must be an admin to use this command.")
#endregion Admin Slash Commands

def main() -> None:
    # Create the Updater and pass it your bot's token
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    
    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher
    
    #region General Slash Command Handlers
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("play", play))
    dispatcher.add_handler(CommandHandler("endgame", end_game))
    dispatcher.add_handler(CommandHandler("tukyo", tukyo))
    dispatcher.add_handler(CommandHandler("tukyogames", tukyogames))
    dispatcher.add_handler(CommandHandler("desypher", deSypher))
    dispatcher.add_handler(CommandHandler("sypher", sypher))
    dispatcher.add_handler(CommandHandler("contract", ca))
    dispatcher.add_handler(CommandHandler("ca", ca))
    dispatcher.add_handler(CommandHandler("chart", chart))
    dispatcher.add_handler(CommandHandler("price", price))
    dispatcher.add_handler(CommandHandler("tokenomics", sypher))
    dispatcher.add_handler(CommandHandler("website", website))
    #endregion General Slash Command Handlers

    #region Admin Slash Command Handlers
    dispatcher.add_handler(CommandHandler('cleargames', cleargames))
    dispatcher.add_handler(CommandHandler('antiraid', antiraid))
    dispatcher.add_handler(CommandHandler("mute", mute))
    dispatcher.add_handler(CommandHandler("unmute", unmute))
    dispatcher.add_handler(CommandHandler("kick", kick))
    #endregion Admin Slash Command Handlers

    # Register the message handler for guesses
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_guess))
    
    # Register the message handler for anti-spam
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    
    # Register the message handler for new users
    dispatcher.add_handler(MessageHandler(Filters.status_update.new_chat_members, handle_new_user))

    # Register the callback query handler for button clicks
    dispatcher.add_handler(CallbackQueryHandler(button_callback, pattern='^verify$'))
    dispatcher.add_handler(CallbackQueryHandler(handle_start_verification, pattern='start_verification'))
    dispatcher.add_handler(CallbackQueryHandler(handle_verification_button, pattern=r'verify_letter_[A-Z]'))
    dispatcher.add_handler(CallbackQueryHandler(handle_start_game, pattern='^startGame$'))
    
    # Start the Bot
    updater.start_polling()
    
    # Run the bot until you press Ctrl-C
    updater.idle()

if __name__ == '__main__':
    main()