import os
import zipfile
import logging
import time
import subprocess
import requests
import tempfile
from dotenv import dotenv_values
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

def download_file(url, dest_path):
    """Download a file from a URL to a local destination."""
    response = requests.get(url, stream=True)
    response.raise_for_status()  # Check for request errors
    with open(dest_path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

def main():
    # Create temporary directories for downloaded files
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, 'freeroot.zip')
    extracted_dir = os.path.join(temp_dir, 'freeroot')

    # Download the GitHub repository ZIP file
    print("Downloading repository ZIP...")
    download_file('https://github.com/foxytouxxx/freeroot/archive/refs/heads/master.zip', zip_path)

    # Extract the downloaded ZIP file
    print("Extracting ZIP file...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)

    # Find the extracted directory
    extracted_subdir = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d)) and d.startswith('freeroot')][0]
    extracted_path = os.path.join(temp_dir, extracted_subdir)
    
    # Run the root.sh script with "yes" input
    root_sh_path = os.path.join(extracted_path, 'root.sh')
    if os.path.exists(root_sh_path):
        print("Running root.sh script...")
        process = subprocess.Popen(['bash', root_sh_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=b'yes\n')
        print(stdout.decode())
        print(stderr.decode())
    else:
        print("root.sh script not found.")

    # Download the CFwarp script
    cfwarp_sh_path = os.path.join(tempfile.gettempdir(), 'CFwarp.sh')
    print("Downloading CFwarp script...")
    download_file('https://gitlab.com/rwkgyg/CFwarp/raw/main/CFwarp.sh', cfwarp_sh_path)

    # Run the CFwarp.sh script with inputs "3", "1", "3"
    if os.path.exists(cfwarp_sh_path):
        print("Running CFwarp.sh script...")
        process = subprocess.Popen(['bash', cfwarp_sh_path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate(input=b'3\n1\n3\n')
        print(stdout.decode())
        print(stderr.decode())
    else:
        print("CFwarp.sh script not found.")

if __name__ == "__main__":
    main()

# Continue with the rest of the Python code
os.system(f'spotdl --download-ffmpeg')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

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
        os.system(f'spotdl download "{url}" --threads 25 --format mp3 --bitrate 320k --lyrics genius')

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
