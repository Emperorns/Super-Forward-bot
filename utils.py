import logging
import re

logger = logging.getLogger(__name__)

class ValidationHelper:
    @staticmethod
    def validate_phone_number(phone):
        """Validate phone number with international format"""
        phone = str(phone).strip()
        phone = phone.replace(" ", "")
        
        # Accept +<country_code><number> format
        # Country code: 1-3 digits, number: 7-12 digits
        if phone.startswith("+") and phone[1:].isdigit() and 10 <= len(phone[1:]) <= 15:
            return True, phone
        
        return False, "Invalid phone format. Use: +<countrycode><number> (e.g., +911234567890)"
    
    @staticmethod
    def validate_verification_code(code):
        """Validate verification code"""
        code = str(code).strip()
        if len(code) >= 4 and code.isdigit():
            return True
        return False
    
    @staticmethod
    def validate_bot_token(token):
        """Validate bot token format"""
        token = str(token).strip()
        if ":" in token and len(token) > 20:
            return True
        return False

class ChannelValidator:
    @staticmethod
    def validate_channel_identifier(identifier):
        """Validate channel username or ID"""
        if not identifier:
            return False, "Channel identifier cannot be empty"
        
        identifier = str(identifier).strip()
        
        # Check if it's a valid username (starts with @)
        if identifier.startswith("@"):
            if len(identifier) < 3:
                return False, "Invalid channel username"
            return True, identifier
        
        # Check if it's a valid numeric ID
        try:
            channel_id = int(identifier)
            if channel_id < -1001000000000:  # Valid Telegram channel ID range
                return False, "Invalid channel ID"
            return True, identifier
        except ValueError:
            return False, "Channel must be username (@channel) or numeric ID"

class ErrorHandler:
    @staticmethod
    def get_error_message(error):
        """Get user-friendly error message"""
        error_str = str(error).lower()
        
        if "flood" in error_str or "rate" in error_str:
            return "Rate limit hit - trying again with delay"
        elif "channel" in error_str or "private" in error_str:
            return "Cannot access channel - check permissions"
        elif "not" in error_str and "authorized" in error_str:
            return "Not logged in - please login first"
        elif "session" in error_str:
            return "Session expired - please login again"
        else:
            return str(error)[:100]
    
    @staticmethod
    def log_error(error, context=""):
        """Log error with context"""
        logger.error(f"[{context}] {type(error).__name__}: {error}")                        
