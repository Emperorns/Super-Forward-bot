from telethon import events
from telethon.errors import SessionPasswordNeededError
import logging
from message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

# Global storage for ongoing authentication
pending_auth = {}

def setup_command_handlers(bot_client, clients, db, task_manager, auth_handler):
    
    @bot_client.on(events.NewMessage(pattern='/start'))
    async def start_handler(event):
        try:
            user_id = event.sender_id
            user_logged_in = await clients.is_user_logged_in()
            bot_logged_in = await clients.is_bot_logged_in()
            
            status = MessageFormatter.format_login_status(user_logged_in, bot_logged_in)
            
            message = (
                "ðŸ¤– TELEGRAM AUTOFORWARD BOT\n\n"
                f"{status}\n\n"
                "Commands:\n"
                "/login_user - Login user account\n"
                "/login_bot - Login bot account\n"
                "/add_user_config - Add user forwarding config\n"
                "/add_bot_config - Add bot forwarding config\n"
                "/list_configs - List all configs\n"
                "/status - Show active tasks\n"
                "/help - Show help\n"
            )
            
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/login_user'))
    async def login_user_handler(event):
        try:
            user_id = event.sender_id
            pending_auth[user_id] = {"step": "phone", "type": "user"}
            
            await event.respond("ðŸ“± Enter your phone number (with country code, e.g., +91xxxxxxxxxx):")
        except Exception as e:
            logger.error(f"Error in login_user handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/login_bot'))
    async def login_bot_handler(event):
        try:
            user_id = event.sender_id
            pending_auth[user_id] = {"step": "token", "type": "bot"}
            
            await event.respond("ðŸ¤– Enter your bot token from @BotFather:")
        except Exception as e:
            logger.error(f"Error in login_bot handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/add_user_config'))
    async def add_user_config_handler(event):
        try:
            user_id = event.sender_id
            pending_auth[user_id] = {"step": "source_channel", "type": "user_config"}
            
            await event.respond("ðŸ“¢ Enter source channel username (e.g., @channel_name):")
        except Exception as e:
            logger.error(f"Error in add_user_config handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/add_bot_config'))
    async def add_bot_config_handler(event):
        try:
            user_id = event.sender_id
            pending_auth[user_id] = {"step": "source_channel", "type": "bot_config"}
            
            await event.respond("ðŸ“¢ Enter source channel username (e.g., @channel_name):")
        except Exception as e:
            logger.error(f"Error in add_bot_config handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/list_configs'))
    async def list_configs_handler(event):
        try:
            user_id = event.sender_id
            configs = await db.get_configs(user_id)
            
            message = MessageFormatter.format_config_list(configs)
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in list_configs handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/status'))
    async def status_handler(event):
        try:
            tasks = await db.get_active_tasks()
            
            message = MessageFormatter.format_task_list(tasks)
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in status handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/help'))
    async def help_handler(event):
        try:
            message = (
                "ðŸ“– HELP\n\n"
                "/start - Start bot\n"
                "/login_user - Login with user account\n"
                "/login_bot - Login with bot token\n"
                "/add_user_config - Add user forwarding config\n"
                "/add_bot_config - Add bot forwarding config\n"
                "/list_configs - Show all configs\n"
                "/status - Show active tasks\n"
            )
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in help handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage())
    async def message_handler(event):
        """Handle multi-step authentication"""
        try:
            if event.is_private:
                user_id = event.sender_id
                message_text = event.text
                
                if user_id not in pending_auth:
                    return
                
                auth_state = pending_auth[user_id]
                step = auth_state.get("step")
                auth_type = auth_state.get("type")
                
                # User account login flow
                if auth_type == "user" and step == "phone":
                    try:
                        success, result = await auth_handler.initiate_user_login(message_text)
                        if success:
                            pending_auth[user_id]["step"] = "code"
                            pending_auth[user_id]["phone"] = message_text
                            await event.respond(f"âœ‰ï¸ {result}")
                        else:
                            await event.respond(MessageFormatter.format_error_message(result))
                            del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error sending code: {e}")
                        await event.respond(MessageFormatter.format_error_message(f"Failed: {e}"))
                        del pending_auth[user_id]
                
                elif auth_type == "user" and step == "code":
                    try:
                        await event.respond("ðŸ” Enter 2FA password (or 'skip' if not enabled):")
                        pending_auth[user_id]["step"] = "password"
                        pending_auth[user_id]["code"] = message_text
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        await event.respond(MessageFormatter.format_error_message(str(e)))
                
                elif auth_type == "user" and step == "password":
                    try:
                        phone = pending_auth[user_id].get("phone")
                        code = pending_auth[user_id].get("code")
                        password = None if message_text.lower() == "skip" else message_text
                        
                        success, result = await auth_handler.verify_user_code(phone, code, password)
                        if success:
                            await event.respond(MessageFormatter.format_success_message(result))
                        else:
                            await event.respond(MessageFormatter.format_error_message(result))
                        
                        del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error logging in: {e}")
                        await event.respond(MessageFormatter.format_error_message(f"Login failed: {e}"))
                        del pending_auth[user_id]
                
                # Bot account login flow
                elif auth_type == "bot" and step == "token":
                    try:
                        success, result = await auth_handler.initiate_bot_login(message_text)
                        if success:
                            await event.respond(MessageFormatter.format_success_message(result))
                        else:
                            await event.respond(MessageFormatter.format_error_message(result))
                        
                        del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error logging in bot: {e}")
                        await event.respond(MessageFormatter.format_error_message(f"Bot login failed: {e}"))
                        del pending_auth[user_id]
                
                # Config creation flow
                elif auth_type in ["user_config", "bot_config"] and step == "source_channel":
                    pending_auth[user_id]["step"] = "dest_channel"
                    pending_auth[user_id]["source_channel"] = message_text
                    await event.respond("ðŸ“¢ Enter destination channel username:")
                
                elif auth_type in ["user_config", "bot_config"] and step == "dest_channel":
                    try:
                        source = pending_auth[user_id].get("source_channel")
                        dest = message_text
                        auth_method = "user_account" if auth_type == "user_config" else "bot_account"
                        user_id_db = user_id
                        
                        config_id = await db.create_config(user_id_db, source, dest, auth_method)
                        await event.respond(
                            MessageFormatter.format_success_message(f"Config created: {config_id}") + 
                            f"\n\nReady to forward!\nUse /status to view and manage tasks."
                        )
                        del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error creating config: {e}")
                        await event.respond(MessageFormatter.format_error_message(str(e)))
                        del pending_auth[user_id]
        
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
