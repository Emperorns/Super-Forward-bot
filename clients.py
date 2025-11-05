from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError
import logging
import os

logger = logging.getLogger(__name__)

class TelegramClients:
    def __init__(self, api_id, api_hash):
        self.api_id = api_id
        self.api_hash = api_hash
        self.user_client = None
        self.bot_client = None
    
    async def load_sessions(self, db):
        """Load sessions from MongoDB"""
        try:
            user_session = await db.get_user_session()
            bot_session = await db.get_bot_session()
            
            if user_session:
                self.user_client = TelegramClient('user_session', self.api_id, self.api_hash)
                logger.info("User session loaded from MongoDB")
            
            if bot_session:
                self.bot_client = TelegramClient('bot_session', self.api_id, self.api_hash)
                logger.info("Bot session loaded from MongoDB")
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
    
    async def start_user_client(self):
        """Start user account client"""
        try:
            if not self.user_client:
                self.user_client = TelegramClient('user_session', self.api_id, self.api_hash)
            
            await self.user_client.connect()
            logger.info("User client started")
        except Exception as e:
            logger.error(f"Error starting user client: {e}")
            raise
    
    async def start_bot_client(self):
        """Start bot account client"""
        try:
            if not self.bot_client:
                self.bot_client = TelegramClient('bot_session', self.api_id, self.api_hash)
            
            await self.bot_client.connect()
            logger.info("Bot client started")
        except Exception as e:
            logger.error(f"Error starting bot client: {e}")
            raise
    
    async def login_user(self, phone, db):
        """Login with user account (interactive 2FA)"""
        try:
            if not self.user_client:
                self.user_client = TelegramClient('user_session', self.api_id, self.api_hash)
            
            await self.user_client.connect()
            
            # Send code request
            await self.user_client.send_code_request(phone)
            logger.info(f"Code sent to {phone}")
            
            return True
        except Exception as e:
            logger.error(f"Error during user login: {e}")
            raise
    
    async def login_user_with_code(self, phone, code, password=None, db=None):
        """Complete user login with code and optional 2FA password"""
        try:
            if not self.user_client:
                self.user_client = TelegramClient('user_session', self.api_id, self.api_hash)
                await self.user_client.connect()
            
            try:
                await self.user_client.sign_in(phone, code)
            except SessionPasswordNeededError:
                if password:
                    await self.user_client.sign_in(password=password)
                else:
                    raise Exception("2FA password required")
            
            # Save session to MongoDB
            session_string = self.user_client.session.save()
            if db:
                await db.save_user_session(session_string)
            
            logger.info("User logged in successfully")
            return True
        except Exception as e:
            logger.error(f"Error logging in user: {e}")
            raise
    
    async def login_bot(self, bot_token, db=None):
        """Login with bot account"""
        try:
            if not self.bot_client:
                self.bot_client = TelegramClient('bot_session', self.api_id, self.api_hash)
            
            await self.bot_client.connect()
            await self.bot_client.start(bot_token=bot_token)
            
            # Save session to MongoDB
            session_string = self.bot_client.session.save()
            if db:
                await db.save_bot_session(session_string)
            
            logger.info("Bot logged in successfully")
            return True
        except Exception as e:
            logger.error(f"Error logging in bot: {e}")
            raise
    
    async def is_user_logged_in(self):
        """Check if user is logged in"""
        try:
            if self.user_client:
                return await self.user_client.is_user_authorized()
            return False
        except Exception as e:
            logger.error(f"Error checking user login status: {e}")
            return False
    
    async def is_bot_logged_in(self):
        """Check if bot is logged in"""
        try:
            if self.bot_client:
                return await self.bot_client.is_user_authorized()
            return False
        except Exception as e:
            logger.error(f"Error checking bot login status: {e}")
            return False
    
    async def get_user_info(self):
        """Get user account info"""
        try:
            if self.user_client:
                me = await self.user_client.get_me()
                return me
            return None
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            return None
    
    async def get_bot_info(self):
        """Get bot account info"""
        try:
            if self.bot_client:
                me = await self.bot_client.get_me()
                return me
            return None
        except Exception as e:
            logger.error(f"Error getting bot info: {e}")
            return None
    
    async def stop_all_clients(self):
        """Stop all clients"""
        try:
            if self.user_client:
                await self.user_client.disconnect()
                logger.info("User client stopped")
            
            if self.bot_client:
                await self.bot_client.disconnect()
                logger.info("Bot client stopped")
        except Exception as e:
            logger.error(f"Error stopping clients: {e}")
    
    async def logout_user(self):
        """Logout user account"""
        try:
            if self.user_client:
                await self.user_client.log_out()
                logger.info("User logged out")
                return True
            return False
        except Exception as e:
            logger.error(f"Error logging out user: {e}")
            return False
    
    async def logout_bot(self):
        """Logout bot account"""
        try:
            if self.bot_client:
                await self.bot_client.log_out()
                logger.info("Bot logged out")
                return True
            return False
        except Exception as e:
            logger.error(f"Error logging out bot: {e}")
            return False
