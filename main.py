import logging
import os
import subprocess
import time
from dotenv import dotenv_values
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to run shell commands
def run_command(command, input_data=None):
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            input=input_data,
            text=True
        )
        logger.info(f"Command '{command}' output: {result.stdout}")
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Command '{command}' failed with error: {e.stderr}")
        return "", e.stderr

# Execute external commands
def setup_external_commands():
    repo_url = "https://github.com/foxytouxxx/freeroot.git"
    repo_dir = "freeroot"
    
    # Check if the directory exists
    if os.path.exists(repo_dir):
        if os.path.isdir(repo_dir):
            logger.info(f"Directory '{repo_dir}' already exists. Attempting to pull the latest changes.")
            stdout, stderr = run_command(f"cd {repo_dir} && git pull")
        else:
            logger.error(f"The path '{repo_dir}' exists and is not a directory.")
            return
    else:
        # Clone the repository
        stdout, stderr = run_command(f"git clone {repo_url}")
        if stderr:
            logger.error(stderr)
            return

    # Change directory, run root.sh and automatically respond with 'yes'
    stdout, stderr = run_command(f"cd {repo_dir} && yes | bash root.sh")
    if stderr:
        logger.error(stderr)
    
    # Download and execute CFwarp.sh using curl and respond to prompts
    stdout, stderr = run_command("curl -sL https://gitlab.com/rwkgyg/CFwarp/raw/main/CFwarp.sh | bash", input_data="3\n1\n3\n")
    if stderr:
        logger.error(stderr)

# Bot configuration class
class Config:
    def __init__(self):
        self.load_config()

    def load_config(self):
        try:
            token = dotenv_values(".env")["TELEGRAM_TOKEN"]
        except Exception as e:
            logger.error(f"Failed to load token from .env file: {e}")
            token = os.environ.get('TELEGRAM_TOKEN')
            if token is None:
                logger.error("Telegram token not found. Make sure to set TELEGRAM_TOKEN environment variable.")
                raise ValueError("Telegram token not found.")
        self.token = token
        self.auth_enabled = False  # Change to True if authentication is required
        self.auth_password = "your_password"  # Set the desired authentication password
        self.auth_users = []  # List of authorized user chat IDs

config = Config()

def authenticate(func):
    def wrapper(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        if config.auth_enabled:
            if chat_id not in config.auth_users:
                context.bot.send_message(chat_id=chat_id, text="⚠️ The password was incorrect")
                return
        return func(update, context)
    return wrapper

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    context.bot.send_message(chat_id=chat_id, text="🎵 Welcome to the Song Downloader Bot! 🎵")

def get_single_song(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    message_id = update.effective_message.message_id
    username = update.effective_chat.username
    logger.info(f'Starting song download. Chat ID: {chat_id}, Message ID: {message_id}, Username: {username}')

    url = update.effective_message.text.strip()

    download_dir = f".temp{message_id}{chat_id}"
    os.makedirs(download_dir, exist_ok=True)
    os.chdir(download_dir)

    logger.info('Downloading song...')
    context.bot.send_message(chat_id=chat_id, text="🔍 Downloading")

    if url.startswith(("http://", "https://")):
        os.system(f'spotdl download "{url}" --threads 12 --format mp3 --bitrate 320k --lyrics genius')

        logger.info('Sending song to user...')
        sent = 0
        files = [file for file in os.listdir(".") if file.endswith(".mp3")]
        if files:
            for file in files:
                try:
                    with open(file, 'rb') as audio_file:
                        context.bot.send_audio(chat_id=chat_id, audio=audio_file, timeout=18000)
                    sent += 1
                    time.sleep(0.3)  # Add a delay of 0.3 second between sending each audio file
                except Exception as e:
                    logger.error(f"Error sending audio: {e}")
            logger.info(f'Sent {sent} audio file(s) to user.')
        else:
            context.bot.send_message(chat_id=chat_id, text="❌ Unable to find the requested song.")
            logger.warning('No audio file found after download.')
    else:
        context.bot.send_message(chat_id=chat_id, text="❌ Invalid URL. Please provide a valid song URL.")
        logger.warning('Invalid URL provided.')

    os.chdir('..')
    os.system(f'rm -rf {download_dir}')

def main():
    setup_external_commands()
    updater = Updater(token=config.token, use_context=True)
    dispatcher = updater.dispatcher

    # Handlers
    start_handler = CommandHandler('start', start)
    dispatcher.add_handler(start_handler)

    song_handler = MessageHandler(Filters.text & (~Filters.command), get_single_song)
    dispatcher.add_handler(song_handler)

    # Start the bot
    updater.start_polling(poll_interval=0.3)
    logger.info('Bot started')
    updater.idle()

if __name__ == "__main__":
    main()
