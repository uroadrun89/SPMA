import os
import subprocess
import logging
import time
from dotenv import dotenv_values
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

def install_wget():
    """Install wget if it is not installed."""
    try:
        subprocess.check_call(["wget", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("wget is already installed.")
    except subprocess.CalledProcessError:
        print("wget is not installed. Installing wget...")
        try:
            subprocess.check_call(["sudo", "apt-get", "update"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.check_call(["sudo", "apt-get", "install", "-y", "wget"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print("wget installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Failed to install wget: {e}")
            raise

def setup_environment():
    install_wget()  # Ensure wget is installed
    
    ROOTFS_DIR = os.getcwd()
    max_retries = 50
    timeout = 1
    ARCH = subprocess.check_output("uname -m", shell=True).decode().strip()

    if ARCH == "x86_64":
        ARCH_ALT = "amd64"
    elif ARCH == "aarch64":
        ARCH_ALT = "arm64"
    else:
        print(f"Unsupported CPU architecture: {ARCH}")
        exit(1)

    if not os.path.exists(f"{ROOTFS_DIR}/.installed"):
        print("#######################################################################################")
        print("#                                      Foxytoux INSTALLER")
        print("#                           Copyright (C) 2024, RecodeStudios.Cloud")
        print("#######################################################################################")
        
        ubuntu_url = f"http://cdimage.ubuntu.com/ubuntu-base/releases/20.04/release/ubuntu-base-20.04.4-base-{ARCH_ALT}.tar.gz"
        try:
            subprocess.check_call(["wget", "--tries=" + str(max_retries), "--timeout=" + str(timeout), "--no-hsts", "-O", "/tmp/rootfs.tar.gz", ubuntu_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.check_call(["tar", "-xf", "/tmp/rootfs.tar.gz", "-C", ROOTFS_DIR], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as e:
            print(f"Failed to download or extract root filesystem: {e}")
            raise

    if not os.path.exists(f"{ROOTFS_DIR}/.installed"):
        os.makedirs(f"{ROOTFS_DIR}/usr/local/bin", exist_ok=True)
        proot_url = f"https://raw.githubusercontent.com/foxytouxxx/freeroot/main/proot-{ARCH}"
        proot_path = f"{ROOTFS_DIR}/usr/local/bin/proot"
        
        for _ in range(max_retries):
            try:
                subprocess.check_call(["wget", "--tries=" + str(max_retries), "--timeout=" + str(timeout), "--no-hsts", "-O", proot_path, proot_url], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if os.path.exists(proot_path) and os.path.getsize(proot_path) > 0:
                    os.chmod(proot_path, 0o755)
                    break
            except subprocess.CalledProcessError as e:
                print(f"Failed to download proot: {e}")
            time.sleep(1)

        os.chmod(proot_path, 0o755)

    if not os.path.exists(f"{ROOTFS_DIR}/.installed"):
        with open(f"{ROOTFS_DIR}/etc/resolv.conf", "w") as resolv_conf:
            resolv_conf.write("nameserver 1.1.1.1\nnameserver 1.0.0.1")
        
        os.system("rm -rf /tmp/rootfs.tar.xz /tmp/sbin")
        open(f"{ROOTFS_DIR}/.installed", "w").close()

    print("\033[0;36m-----> Mission Completed! <-----\033[0m")

# Telegram Bot Code
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
    setup_environment()

    # Ensure spotdl and ffmpeg are downloaded
    os.system('spotdl --download-ffmpeg')

    # Set up logging
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)

    main()
