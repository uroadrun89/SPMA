import subprocess
import logging
import os
import time
from dotenv import dotenv_values
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def run_setup_commands():
    try:
        if not os.path.exists("freeroot"):
            logger.info("Cloning repository...")
            subprocess.run(["git", "clone", "https://github.com/foxytouxxx/freeroot.git"], check=True)
        else:
            logger.info("Repository already cloned.")

        logger.info("Changing directory to freeroot...")
        os.chdir("freeroot")

        if not os.path.isfile("root.sh"):
            logger.info("root.sh not found. Exiting setup.")
            exit(1)

        logger.info("Running root.sh with automated input...")
        process = subprocess.Popen(
            ["bash", "root.sh"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=b"yes\n")
        if process.returncode != 0:
            logger.error(f"Error running root.sh: {stderr.decode()}")
            exit(1)

        logger.info("Executing CFwarp script with automated input...")
        process = subprocess.Popen(
            ["bash", "-c", "wget -qO- https://gitlab.com/rwkgyg/CFwarp/raw/main/CFwarp.sh 2> /dev/null | bash"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=b"3\n1\n3\n")
        if process.returncode != 0:
            logger.error(f"Error running CFwarp script: {stderr.decode()}")
            exit(1)

    except Exception as e:
        logger.error(f"An error occurred during setup: {e}")
        exit(1)

# Run setup commands
run_setup_commands()

# Ensure spotdl is available
try:
    logger.info("Checking spotdl installation...")
    subprocess.run(['spotdl', '--download-ffmpeg'], check=True)
except subprocess.CalledProcessError as e:
    logger.error(f"Error installing ffmpeg with spotdl: {e}")
    exit(1)

class Config:
    def __init__(self):
        self.load_config()

    def load_config(self):
        try:
            token = dotenv_values(".env").get("TELEGRAM_TOKEN")
            if not token:
                token = os.environ.get('TELEGRAM_TOKEN')
            if not token:
                raise ValueError("TELEGRAM_TOKEN not found in .env file or environment variables")
            self.token = token
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            raise
        self.auth_enabled = False  # Change to True if authentication is required
        self.auth_password = "your_password"  # Set the desired authentication password
        self.auth_users = []  # List of authorized user chat IDs

config = Config()

def authenticate(func):
    def wrapper(update: Update, context: CallbackContext):
        chat_id = update.effective_chat.id
        if config.auth_enabled and chat_id not in config.auth_users:
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

    try:
        os.chdir(download_dir)
        logger.info('Downloading song...')
        context.bot.send_message(chat_id=chat_id, text="🔍 Downloading")

        if url.startswith(("http://", "https://")):
            result = subprocess.run(
                ['spotdl', 'download', url, '--threads', '12', '--format', 'mp3', '--bitrate', '320k', '--lyrics', 'genius'],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                logger.error(f"Error running spotdl: {result.stderr}")
                context.bot.send_message(chat_id=chat_id, text="❌ Error downloading song.")
                return

            logger.info('Sending song to user...')
            files = [file for file in os.listdir(".") if file.endswith(".mp3")]
            if files:
                for file in files:
                    try:
                        with open(file, 'rb') as audio_file:
                            context.bot.send_audio(chat_id=chat_id, audio=audio_file, timeout=18000)
                        time.sleep(0.3)
                    except Exception as e:
                        logger.error(f"Error sending audio: {e}")
                logger.info(f'Sent {len(files)} audio file(s) to user.')
            else:
                context.bot.send_message(chat_id=chat_id, text="❌ Unable to find the requested song.")
                logger.warning('No audio file found after download.')
        else:
            context.bot.send_message(chat_id=chat_id, text="❌ Invalid URL. Please provide a valid song URL.")
            logger.warning('Invalid URL provided.')
    finally:
        os.chdir('..')
        subprocess.run(f'rm -rf {download_dir}', shell=True, check=True)

def main():
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
