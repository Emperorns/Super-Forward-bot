from telethon.errors import SessionPasswordNeededError, FloodWaitError
import logging
from utils import ValidationHelper, ErrorHandler

logger = logging.getLogger(__name__)

class AuthenticationHandler:
    def __init__(self, clients, db):
        self.clients = clients
        self.db = db
    
    async def initiate_user_login(self, phone):
        """Initiate user login with phone number"""
        try:
            is_valid, phone_or_error = ValidationHelper.validate_phone_number(phone)
            if not is_valid:
                return False, phone_or_error
            
            # Send code request
            await self.clients.login_user(phone_or_error, self.db)
            logger.info(f"Code sent to {phone_or_error}")
            return True, "Verification code sent to your Telegram app"
        
        except FloodWaitError as e:
            error_msg = f"Rate limited. Wait {e.seconds} seconds"
            logger.warning(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = ErrorHandler.get_error_message(e)
            logger.error(f"Error initiating login: {e}")
            return False, error_msg
    
    async def verify_user_code(self, phone, code, password=None):
        """Verify user login with code and optional 2FA password"""
        try:
            is_valid = ValidationHelper.validate_verification_code(code)
            if not is_valid:
                return False, "Invalid verification code format"
            
            # Login with code
            await self.clients.login_user_with_code(phone, code, password, self.db)
            logger.info(f"User logged in successfully")
            return True, "User account logged in successfully!"
        
        except SessionPasswordNeededError:
            logger.warning("2FA password needed")
            return False, "2FA_REQUIRED"
        except Exception as e:
            error_msg = ErrorHandler.get_error_message(e)
            logger.error(f"Error verifying code: {e}")
            return False, error_msg
    
    async def initiate_bot_login(self, bot_token):
        """Initiate bot login"""
        try:
            is_valid = ValidationHelper.validate_bot_token(bot_token)
            if not is_valid:
                return False, "Invalid bot token format"
            
            await self.clients.login_bot(bot_token, self.db)
            logger.info("Bot logged in successfully")
            return True, "Bot account logged in successfully!"
        
        except Exception as e:
            error_msg = ErrorHandler.get_error_message(e)
            logger.error(f"Error logging in bot: {e}")
            return False, error_msg
    
    async def check_login_status(self):
        """Check both account login status"""
        try:
            user_logged_in = await self.clients.is_user_logged_in()
            bot_logged_in = await self.clients.is_bot_logged_in()
            
            return {
                "user_logged_in": user_logged_in,
                "bot_logged_in": bot_logged_in
            }
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return {
                "user_logged_in": False,
                "bot_logged_in": False
            }
