import asyncio
import logging
import sys
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
import os
from dotenv import load_dotenv
from aiohttp import web
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

# Load environment variables with error checking
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
MONGODB_URI = os.getenv('MONGODB_URI')
PORT = int(os.getenv('PORT', 8080))

# Validate that all required variables are set
if not API_ID:
    logger.error("ERROR: API_ID not set in environment variables")
    sys.exit(1)
if not API_HASH:
    logger.error("ERROR: API_HASH not set in environment variables")
    sys.exit(1)
if not BOT_TOKEN:
    logger.error("ERROR: BOT_TOKEN not set in environment variables")
    sys.exit(1)
if not MONGODB_URI:
    logger.error("ERROR: MONGODB_URI not set in environment variables")
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.error("ERROR: API_ID must be a number")
    sys.exit(1)

MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'forwarder_bot')

logger.info(f"API_ID: {API_ID}")
logger.info(f"API_HASH: {API_HASH[:10]}...")
logger.info(f"BOT_TOKEN: {BOT_TOKEN[:20]}...")
logger.info(f"MONGODB_URI: {MONGODB_URI[:30]}...")
logger.info(f"PORT: {PORT}")

class ForwarderBot:
    def __init__(self):
        self.clients = TelegramClients(API_ID, API_HASH)
        self.db = Database(MONGODB_URI, MONGODB_DB_NAME)
        self.task_manager = TaskManager(self.clients, self.db)
        self.auth_handler = AuthenticationHandler(self.clients, self.db)
        self.bot_client = None
        self.app = None
        self.is_healthy = False
        
    async def health_check(self, request):
        """Health check endpoint for Koyeb"""
        if self.is_healthy:
            return web.json_response({"status": "healthy"}, status=200)
        else:
            return web.json_response({"status": "starting"}, status=503)
    
    async def setup_web_server(self):
        """Setup aiohttp web server for health checks"""
        self.app = web.Application()
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/', self.health_check)
        
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', PORT)
        await site.start()
        logger.info(f"Web server started on port {PORT}")
        return runner
    
    async def start(self):
        try:
            logger.info("Starting Forwarder Bot...")
            
            # Start web server first
            runner = await self.setup_web_server()
            
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
                try:
                    await self.clients.start_user_client()
                    logger.info("User account client started")
                except Exception as e:
                    logger.warning(f"Could not start user client: {e}")
            else:
                logger.info("User session not found - login required")
            
            if bot_session_exists:
                try:
                    await self.clients.start_bot_client()
                    logger.info("Bot account client started")
                except Exception as e:
                    logger.warning(f"Could not start bot client: {e}")
            else:
                logger.info("Bot session not found - login required")
            
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
            
            # Mark as healthy
            self.is_healthy = True
            logger.info("=" * 50)
            logger.info("ðŸ¤– FORWARDER BOT STARTED SUCCESSFULLY!")
            logger.info("=" * 50)
            
            # Keep running
            await self.bot_client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Error starting bot: {e}", exc_info=True)
            self.is_healthy = False
            raise
    
    async def stop(self):
        try:
            logger.info("Stopping Forwarder Bot...")
            self.is_healthy = False
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
        logger.error(f"Fatal error: {e}", exc_info=True)
        await bot.stop()

if __name__ == "__main__":
    asyncio.run(main())            
