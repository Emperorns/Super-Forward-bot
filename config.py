import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv('API_ID', '22711559'))
API_HASH = os.getenv('API_HASH', '07f916d610702eb4b0678bdf32c895c1')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb+srv://Movil:nehalsingh969797@cluster0.z9r4vyp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0')
MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'forwarder_bot')

# Rate Limiting Config
RATE_LIMITS = {
    "user_account": {
        "base_delay": 1.0,
        "min_delay": 0.5,
        "max_delay": 3.0,
        "batch_size": 50,
        "batch_cooldown": 10,
        "max_forwards_per_minute": 40,
        "backoff_multiplier": 2.0
    },
    "bot_account": {
        "base_delay": 0.3,
        "min_delay": 0.1,
        "max_delay": 1.0,
        "batch_size": 100,
        "batch_cooldown": 5,
        "max_forwards_per_minute": 80,
        "backoff_multiplier": 1.5
    }
}

# Task settings
MAX_RETRIES = 5
TASK_TIMEOUT = 3600
PROGRESS_UPDATE_BATCH = 100
