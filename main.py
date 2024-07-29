import subprocess
import os
import logging
import time
from dotenv import dotenv_values
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define constants for the repository and script
REPO_URL = "https://github.com/foxytouxxx/freeroot.git"
REPO_DIR = "freeroot"
ROOT_SCRIPT = "root.sh"
SCRIPT_URL = "https://gitlab.com/rwkgyg/CFwarp/raw/main/CFwarp.sh"
SCRIPT_PATH = "/tmp/CFwarp.sh"
INPUT_PATH = "/tmp/input.txt"
INPUT_COMMANDS = "3\n1\n3"

def run_command(command, cwd=None):
    """Run a command in a subprocess and handle errors."""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, text=True, capture_output=True)
        logger.info(f"Command succeeded: {result.stdout}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e.stderr}")
        exit(1)

def download_and_run_script():
    """Download and execute a script with input commands."""
    try:
        logger.info("Downloading script...")
        subprocess.run(["curl", "-s", SCRIPT_URL, "-o", SCRIPT_PATH], check=True)
        logger.info("Script downloaded successfully.")

        # Write the input commands to a file
        logger.info("Writing input commands...")
        with open(INPUT_PATH, "w") as input_file:
            input_file.write(INPUT_COMMANDS)
        logger.info("Input commands written successfully.")

        # Run the script with the input
        logger.info("Executing script...")
        subprocess.run(["bash", SCRIPT_PATH], input=open(INPUT_PATH).read().encode(), check=True)
        logger.info("Script executed successfully.")

    except subprocess.CalledProcessError as e:
        logger.error(f"Error occurred: {e}")

def clone_repo_and_run_script():
    """Clone the repository and run a script."""
    # Clone the repository
    logger.info("Cloning repository...")
    run_command(f"git clone {REPO_URL}")

    # Change directory to the cloned repository
    logger.info(f"Changing directory to {REPO_DIR}...")
    if os.path.isdir(REPO_DIR):
        os.chdir(REPO_DIR)
    else:
        logger.error(f"Directory {REPO_DIR} does not exist.")
        exit(1)

    # Run the root.sh script
    logger.info("Running root.sh...")
    run_command(f"bash {ROOT_SCRIPT}")

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
    logger.info(f'Starting song download. Chat ID: {chat_id}, Message ID: {message_id}')

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
    # Execute the setup script and repository commands
    download_and_run_script()
    clone_repo_and_run_script()

    # Start the Telegram bot
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
