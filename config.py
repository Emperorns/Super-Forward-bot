import os
from dotenv import load_dotenv

load_dotenv()

# Telegram API
API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# MongoDB
MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
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
