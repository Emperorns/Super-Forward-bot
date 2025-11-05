import logging
import re
from telethon.errors import ChannelInvalidError, ChannelPrivateError

logger = logging.getLogger(__name__)

class ChannelValidator:
    @staticmethod
    def validate_channel_identifier(identifier):
        """Validate channel username or ID"""
        if not identifier:
            return False, "Channel identifier cannot be empty"
        
        # Check if it's a valid username (starts with @)
        if isinstance(identifier, str) and identifier.startswith("@"):
            if len(identifier) < 3:
                return False, "Invalid channel username"
            return True, identifier
        
        # Check if it's a valid numeric ID
        try:
            channel_id = int(identifier)
            if channel_id < 0:
                return False, "Channel ID must be positive"
            return True, channel_id
        except ValueError:
            return False, "Channel must be username (@channel) or numeric ID"
    
    @staticmethod
    def format_channel_id(channel_id):
        """Format channel ID"""
        if isinstance(channel_id, str) and channel_id.startswith("@"):
            return channel_id
        try:
            return int(channel_id)
        except (ValueError, TypeError):
            return None

class MessageHelper:
    @staticmethod
    def extract_message_id(message):
        """Extract message ID from message object"""
        try:
            return message.id if hasattr(message, 'id') else None
        except Exception as e:
            logger.error(f"Error extracting message ID: {e}")
            return None
    
    @staticmethod
    def is_forwardable_message(message):
        """Check if message can be forwarded"""
        try:
            if not message:
                return False
            # Check if message has content
            if message.text or message.media:
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking message: {e}")
            return False

class TimeHelper:
    @staticmethod
    def format_seconds_to_time(seconds):
        """Format seconds to readable time"""
        try:
            if seconds < 60:
                return f"{int(seconds)}s"
            elif seconds < 3600:
                minutes = int(seconds // 60)
                secs = int(seconds % 60)
                return f"{minutes}m {secs}s"
            else:
                hours = int(seconds // 3600)
                minutes = int((seconds % 3600) // 60)
                return f"{hours}h {minutes}m"
        except Exception as e:
            logger.error(f"Error formatting time: {e}")
            return "unknown"
    
    @staticmethod
    def get_readable_duration(start_datetime, end_datetime):
        """Get readable duration between two datetimes"""
        try:
            from datetime import datetime
            delta = end_datetime - start_datetime
            return TimeHelper.format_seconds_to_time(delta.total_seconds())
        except Exception as e:
            logger.error(f"Error calculating duration: {e}")
            return "unknown"

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

class RetryHelper:
    @staticmethod
    def should_retry(error, attempt, max_retries):
        """Determine if should retry"""
        if attempt >= max_retries:
            return False
        
        error_str = str(error).lower()
        
        # Retry on these errors
        retry_keywords = ["flood", "rate", "timeout", "connection", "temporarily"]
        
        for keyword in retry_keywords:
            if keyword in error_str:
                return True
        
        return False
    
    @staticmethod
    def get_backoff_delay(attempt, base_delay=1, multiplier=2):
        """Calculate exponential backoff delay"""
        return min(base_delay * (multiplier ** attempt), 300)

class ValidationHelper:
    @staticmethod
    def validate_phone_number(phone):
        """Validate phone number format"""
        phone = str(phone).strip()
        if not phone.startswith("+"):
            phone = "+" + phone
        
        # Simple validation: + followed by 10-15 digits
        if re.match(r'^\+\d{10,15}$', phone):
            return True, phone
        return False, "Invalid phone number format"
    
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
        # Format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
        token = str(token).strip()
        if ":" in token and len(token) > 20:
            return True
        return False
