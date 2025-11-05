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
            config_id = task.get("config_id", "Unknown")
            status = task.get("status", "UNKNOWN")
            task_type = task.get("type", "unknown")
            
            progress = task.get("progress", {})
            forwarded = progress.get("forwarded_count", 0)
            total = progress.get("total_messages", 0)
            last_msg_id = progress.get("last_forwarded_message_id", 0)
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
                f"ðŸ“Š TASK: {config_id}\n"
                f"Type: {task_type.upper()} | Status: {status_emoji} {status}\n"
                f"Progress: {progress_bar}\n"
                f"Forwarded: {forwarded:,} / {total:,}\n"
                f"Est. Time: {time_remaining}\n"
            )
            
            return message
        except Exception as e:
            logger.error(f"Error formatting task status: {e}")
            return "Error formatting status"
    
    @staticmethod
    def format_config_list(configs):
        """Format configuration list"""
        try:
            if not configs:
                return "No configurations found."
            
            message = "ðŸ“‹ YOUR CONFIGURATIONS:\n\n"
            
            for i, config in enumerate(configs, 1):
                config_id = config.get("_id", "Unknown")
                source = config.get("source_channel", "Unknown")
                dest = config.get("dest_channel", "Unknown")
                auth = config.get("auth_method", "Unknown")
                
                message += (
                    f"{i}. ID: {config_id}\n"
                    f"   From: {source}\n"
                    f"   To: {dest}\n"
                    f"   Auth: {auth}\n\n"
                )
            
            return message
        except Exception as e:
            logger.error(f"Error formatting config list: {e}")
            return "Error formatting configuration list"
    
    @staticmethod
    def format_task_list(tasks):
        """Format active task list"""
        try:
            if not tasks:
                return "No active tasks."
            
            message = "ðŸ“Š ACTIVE TASKS:\n\n"
            
            for task in tasks:
                message += MessageFormatter.format_task_status(task) + "\n"
            
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
        bot_status = "âœ… Logged in" if bot_logged_in else "âŒ Not logged in"
        
        return (
            f"ðŸ”‘ USER ACCOUNT: {user_status}\n"
            f"ðŸ¤– BOT ACCOUNT: {bot_status}"
        )
    
    @staticmethod
    def build_task_buttons(task_id):
        """Build inline buttons for task control"""
        buttons = [
            [
                {"text": "â¸ï¸ Pause", "callback_data": f"pause_{task_id}"},
                {"text": "â¹ï¸ Stop", "callback_data": f"stop_{task_id}"}
            ],
            [
                {"text": "ðŸ”„ Refresh", "callback_data": f"refresh_{task_id}"},
                {"text": "ðŸ—‘ï¸ Delete", "callback_data": f"delete_{task_id}"}
            ]
        ]
        return buttons
    
    @staticmethod
    def build_main_menu_buttons():
        """Build main menu buttons"""
        buttons = [
            [
                {"text": "ðŸ” Status", "callback_data": "status"},
                {"text": "âš™ï¸ Manage", "callback_data": "manage"}
            ],
            [
                {"text": "âž• New Task", "callback_data": "new_task"}
            ]
        ]
        return buttons
