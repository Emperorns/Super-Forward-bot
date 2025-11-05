from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class MessageFormatter:
    
    @staticmethod
    def format_progress_bar(current, total, width=10):
        """Create progress bar"""
        if total == 0:
            percentage = 0
            filled = 0
        else:
            percentage = (current / total) * 100
            filled = int((current / total) * width)
        
        bar = 'â–ˆ' * filled + 'â–‘' * (width - filled)
        return f"{bar} {percentage:.1f}%"
    
    @staticmethod
    def format_time_remaining(current, total, elapsed_seconds):
        """Calculate and format estimated time remaining"""
        try:
            if current == 0 or elapsed_seconds == 0:
                return "calculating..."
            
            rate = current / elapsed_seconds
            remaining = (total - current) / rate
            
            if remaining < 0:
                return "done"
            
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            
            if hours > 0:
                return f"~{hours}h {minutes}m"
            else:
                return f"~{minutes}m"
        except Exception as e:
            logger.error(f"Error calculating time: {e}")
            return "calculating..."
    
    @staticmethod
    def format_task_status(task):
        """Format task status for display"""
        try:
            source = task.get("source_channel", "Unknown")
            dest = task.get("dest_channel", "Unknown")
            status = task.get("status", "UNKNOWN")
            task_type = task.get("type", "unknown")
            
            progress = task.get("progress", {})
            forwarded = progress.get("forwarded_count", 0)
            total = progress.get("total_messages", 0)
            start_time = task.get("created_at")
            
            # Calculate elapsed time
            if start_time:
                elapsed = (datetime.utcnow() - start_time).total_seconds()
            else:
                elapsed = 0
            
            # Format progress bar
            progress_bar = MessageFormatter.format_progress_bar(forwarded, total)
            
            # Format time remaining
            time_remaining = MessageFormatter.format_time_remaining(forwarded, total, elapsed)
            
            # Status emoji
            status_emoji = {
                "RUNNING": "â–¶ï¸",
                "PAUSED": "â¸ï¸",
                "COMPLETED": "âœ…",
                "ERROR": "âŒ",
                "STOPPED": "â¹ï¸"
            }.get(status, "â“")
            
            message = (
                f"ðŸ“Š TASK\n"
                f"From: {source}\n"
                f"To: {dest}\n"
                f"Type: {task_type.upper()}\n"
                f"Status: {status_emoji} {status}\n\n"
                f"Progress: {progress_bar}\n"
                f"Forwarded: {forwarded:,} / {total:,}\n"
                f"Est. Time: {time_remaining}\n"
            )
            
            return message
        except Exception as e:
            logger.error(f"Error formatting task status: {e}")
            return "Error formatting status"
    
    @staticmethod
    def format_task_list(tasks):
        """Format active task list"""
        try:
            if not tasks:
                return "No active tasks."
            
            message = "ðŸ“Š ACTIVE TASKS:\n\n"
            
            for i, task in enumerate(tasks, 1):
                message += f"{i}. {MessageFormatter.format_task_status(task)}\n"
            
            return message
        except Exception as e:
            logger.error(f"Error formatting task list: {e}")
            return "Error formatting task list"
    
    @staticmethod
    def format_error_message(error_text):
        """Format error message"""
        return f"âŒ ERROR: {error_text}"
    
    @staticmethod
    def format_success_message(text):
        """Format success message"""
        return f"âœ… {text}"
    
    @staticmethod
    def format_login_status(user_logged_in, bot_logged_in):
        """Format login status"""
        user_status = "âœ… Logged in" if user_logged_in else "âŒ Not logged in"
        bot_status = "âœ… Active" if bot_logged_in else "âŒ Not active"
        
        return (
            f"ðŸ”‘ USER ACCOUNT: {user_status}\n"
            f"ðŸ¤– BOT ACCOUNT: {bot_status}"
        )        
