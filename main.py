import asyncio
import logging
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import os
from dotenv import load_dotenv
from clients import TelegramClients
from command_handlers import setup_command_handlers
from button_handlers import setup_button_handlers
from task_manager import TaskManager
from database import Database
from auth import AuthenticationHandler
from logger import setup_logger

load_dotenv()
setup_logger()
logger = logging.getLogger(__name__)

API_ID = int(os.getenv('API_ID'))
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')

class ForwarderBot:
    def __init__(self):
        self.clients = TelegramClients(API_ID, API_HASH)
        self.db = Database(MONGODB_URI)
        self.task_manager = TaskManager(self.clients, self.db)
        self.auth_handler = AuthenticationHandler(self.clients, self.db)
        self.bot_client = None
        
    async def start(self):
        try:
            logger.info("Starting Forwarder Bot...")
            
            # Initialize database connection
            await self.db.connect()
            logger.info("Database connected")
            
            # Load sessions from MongoDB
            await self.clients.load_sessions(self.db)
            logger.info("Sessions loaded")
            
            # Start both Telethon clients (if sessions exist)
            user_session_exists = await self.db.session_exists('user')
            bot_session_exists = await self.db.session_exists('bot')
            
            if user_session_exists:
                await self.clients.start_user_client()
                logger.info("User account client started")
            
            if bot_session_exists:
                await self.clients.start_bot_client()
                logger.info("Bot account client started")
            
            # Initialize bot client for handlers
            self.bot_client = TelegramClient('bot_handler', API_ID, API_HASH)
            await self.bot_client.start(bot_token=BOT_TOKEN)
            logger.info("Bot handler client started")
            
            # Setup task manager
            await self.task_manager.initialize()
            logger.info("Task manager initialized")
            
            # Resume interrupted tasks
            await self.task_manager.resume_tasks()
            logger.info("Resumed interrupted tasks")
            
            # Setup handlers
            setup_command_handlers(self.bot_client, self.clients, self.db, self.task_manager, self.auth_handler)
            setup_button_handlers(self.bot_client, self.clients, self.db, self.task_manager)
            logger.info("Command and button handlers registered")
            
            logger.info("Forwarder Bot started successfully")
            
            # Keep running
            await self.bot_client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}")
            raise
    
    async def stop(self):
        try:
            logger.info("Stopping Forwarder Bot...")
            await self.task_manager.pause_all_tasks()
            await self.clients.stop_all_clients()
            await self.db.close()
            logger.info("Bot stopped successfully")
        except Exception as e:
            logger.error(f"Error stopping bot: {e}")

async def main():
    bot = ForwarderBot()
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await bot.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())
