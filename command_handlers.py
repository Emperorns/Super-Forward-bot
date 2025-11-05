from telethon import events
from telethon.errors import SessionPasswordNeededError
import logging
from message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

# Global storage for ongoing multi-step processes
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
                "ðŸ“‹ COMMANDS:\n\n"
                "ðŸ” LOGIN:\n"
                "/login_user - Login with user account (phone + 2FA)\n"
                "/login_bot - Login with bot token\n\n"
                "âš™ï¸ CONFIGURATION:\n"
                "/add_user_config - Setup user account forwarding\n"
                "/add_bot_config - Setup bot account forwarding\n"
                "/list_configs - View all configurations\n\n"
                "ðŸ“Š MANAGEMENT:\n"
                "/status - Show active tasks\n"
                "/help - Show help\n"
            )
            
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    # ==================== LOGIN HANDLERS ====================
    
    @bot_client.on(events.NewMessage(pattern='/login_user'))
    async def login_user_handler(event):
        try:
            user_id = event.sender_id
            
            # Check if already logged in
            already_logged = await clients.is_user_logged_in()
            if already_logged:
                await event.respond("âœ… User account already logged in!")
                return
            
            pending_auth[user_id] = {
                "step": "phone",
                "type": "user_login",
                "phone": None,
                "code": None
            }
            
            await event.respond(
                "ðŸ“± STEP 1/3: Enter your phone number\n"
                "Format: +91xxxxxxxxxx (with country code)\n\n"
                "Example: +911234567890"
            )
        except Exception as e:
            logger.error(f"Error in login_user handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/login_bot'))
    async def login_bot_handler(event):
        try:
            user_id = event.sender_id
            
            # Check if already logged in
            already_logged = await clients.is_bot_logged_in()
            if already_logged:
                await event.respond("âœ… Bot account already logged in!")
                return
            
            pending_auth[user_id] = {
                "step": "token",
                "type": "bot_login"
            }
            
            await event.respond(
                "ðŸ¤– ENTER BOT TOKEN\n\n"
                "Get it from @BotFather:\n"
                "1. Send /start to @BotFather\n"
                "2. Send /newbot or select existing bot\n"
                "3. Copy the token\n"
                "4. Send it here\n\n"
                "Format: 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef"
            )
        except Exception as e:
            logger.error(f"Error in login_bot handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    # ==================== CONFIG HANDLERS ====================
    
    @bot_client.on(events.NewMessage(pattern='/add_user_config'))
    async def add_user_config_handler(event):
        try:
            user_id = event.sender_id
            
            # Check if user is logged in
            logged_in = await clients.is_user_logged_in()
            if not logged_in:
                await event.respond(
                    "âŒ User account not logged in!\n\n"
                    "Please login first:\n/login_user"
                )
                return
            
            pending_auth[user_id] = {
                "step": "source",
                "type": "user_config",
                "source_channel": None,
                "dest_channel": None
            }
            
            await event.respond(
                "ðŸ“¢ STEP 1/2: Enter SOURCE channel\n"
                "(Channel to forward messages FROM)\n\n"
                "Enter channel username or ID:\n"
                "â€¢ @channel_name\n"
                "â€¢ -1001234567890\n\n"
                "Example: @news_channel"
            )
        except Exception as e:
            logger.error(f"Error in add_user_config handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/add_bot_config'))
    async def add_bot_config_handler(event):
        try:
            user_id = event.sender_id
            
            # Check if bot is logged in
            logged_in = await clients.is_bot_logged_in()
            if not logged_in:
                await event.respond(
                    "âŒ Bot account not logged in!\n\n"
                    "Please login first:\n/login_bot"
                )
                return
            
            pending_auth[user_id] = {
                "step": "source",
                "type": "bot_config",
                "source_channel": None,
                "dest_channel": None
            }
            
            await event.respond(
                "ðŸ“¢ STEP 1/2: Enter SOURCE channel\n"
                "(Channel to forward messages FROM)\n\n"
                "Enter channel username or ID:\n"
                "â€¢ @channel_name\n"
                "â€¢ -1001234567890\n\n"
                "Example: @public_channel"
            )
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
            
            if not tasks:
                await event.respond("ðŸ“Š No active tasks")
                return
            
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
                "ðŸ” LOGIN COMMANDS:\n"
                "/login_user - Login with phone number\n"
                "/login_bot - Login with bot token\n\n"
                "âš™ï¸ CONFIG COMMANDS:\n"
                "/add_user_config - Add user forwarding config\n"
                "/add_bot_config - Add bot forwarding config\n"
                "/list_configs - View all configs\n\n"
                "ðŸ“Š MANAGEMENT:\n"
                "/status - Show active forwarding tasks\n"
                "/start - Show main menu\n\n"
                "ðŸ’¡ TIPS:\n"
                "â€¢ Login first before adding configs\n"
                "â€¢ Each config = one forwarding path\n"
                "â€¢ You can have multiple configs\n"
            )
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in help handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    # ==================== MESSAGE HANDLER (Multi-step flow) ====================
    
    @bot_client.on(events.NewMessage())
    async def message_handler(event):
        """Handle multi-step authentication and configuration"""
        try:
            if not event.is_private:
                return
            
            user_id = event.sender_id
            message_text = event.text.strip()
            
            if user_id not in pending_auth:
                return
            
            auth_state = pending_auth[user_id]
            auth_type = auth_state.get("type")
            step = auth_state.get("step")
            
            # ========== USER LOGIN FLOW ==========
            if auth_type == "user_login":
                
                # STEP 1: Collect phone
                if step == "phone":
                    try:
                        success, result = await auth_handler.initiate_user_login(message_text)
                        if success:
                            pending_auth[user_id]["phone"] = message_text
                            pending_auth[user_id]["step"] = "code"
                            await event.respond(
                                "âœ… Code sent to your Telegram app!\n\n"
                                "ðŸ“± STEP 2/3: Enter verification code\n"
                                "(5-digit code sent to your Telegram)\n\n"
                                "Example: 12345"
                            )
                        else:
                            await event.respond(MessageFormatter.format_error_message(result))
                            del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error sending code: {e}")
                        await event.respond(MessageFormatter.format_error_message(f"Failed to send code: {e}"))
                        del pending_auth[user_id]
                
                # STEP 2: Collect code
                elif step == "code":
                    try:
                        phone = pending_auth[user_id].get("phone")
                        if not phone:
                            await event.respond("âŒ Error: Phone number lost")
                            del pending_auth[user_id]
                            return
                        
                        pending_auth[user_id]["code"] = message_text
                        pending_auth[user_id]["step"] = "password"
                        
                        await event.respond(
                            "âœ… Code received!\n\n"
                            "ðŸ” STEP 3/3: Enter 2FA password\n"
                            "(Or type 'skip' if 2FA not enabled)\n\n"
                            "If 2FA is disabled, just type: skip"
                        )
                    except Exception as e:
                        logger.error(f"Error: {e}")
                        await event.respond(MessageFormatter.format_error_message(str(e)))
                
                # STEP 3: Collect password / Complete login
                elif step == "password":
                    try:
                        phone = pending_auth[user_id].get("phone")
                        code = pending_auth[user_id].get("code")
                        password = None if message_text.lower() == "skip" else message_text
                        
                        success, result = await auth_handler.verify_user_code(phone, code, password)
                        
                        if success:
                            await event.respond(
                                f"âœ… {result}\n\n"
                                "User account is now active!\n"
                                "You can now:\n"
                                "/add_user_config - Setup forwarding"
                            )
                        else:
                            await event.respond(MessageFormatter.format_error_message(result))
                        
                        del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error logging in: {e}")
                        await event.respond(MessageFormatter.format_error_message(f"Login failed: {e}"))
                        del pending_auth[user_id]
            
            # ========== BOT LOGIN FLOW ==========
            elif auth_type == "bot_login":
                if step == "token":
                    try:
                        success, result = await auth_handler.initiate_bot_login(message_text)
                        
                        if success:
                            await event.respond(
                                f"âœ… {result}\n\n"
                                "Bot account is now active!\n"
                                "You can now:\n"
                                "/add_bot_config - Setup forwarding"
                            )
                        else:
                            await event.respond(MessageFormatter.format_error_message(result))
                        
                        del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error logging in bot: {e}")
                        await event.respond(MessageFormatter.format_error_message(f"Bot login failed: {e}"))
                        del pending_auth[user_id]
            
            # ========== USER CONFIG FLOW ==========
            elif auth_type == "user_config":
                
                # STEP 1: Collect source channel
                if step == "source":
                    pending_auth[user_id]["source_channel"] = message_text
                    pending_auth[user_id]["step"] = "dest"
                    
                    await event.respond(
                        f"âœ… Source: {message_text}\n\n"
                        "ðŸ“¢ STEP 2/2: Enter DESTINATION channel\n"
                        "(Channel to forward messages TO)\n\n"
                        "Enter channel username or ID:\n"
                        "â€¢ @channel_name\n"
                        "â€¢ -1001234567890\n\n"
                        "Example: @my_archive"
                    )
                
                # STEP 2: Collect destination and create config
                elif step == "dest":
                    try:
                        source = pending_auth[user_id].get("source_channel")
                        dest = message_text
                        
                        if not source:
                            await event.respond("âŒ Error: Source channel lost")
                            del pending_auth[user_id]
                            return
                        
                        config_id = await db.create_config(
                            user_id, source, dest, "user_account"
                        )
                        
                        await event.respond(
                            f"âœ… Configuration Created!\n\n"
                            f"Config ID: {config_id}\n"
                            f"From: {source}\n"
                            f"To: {dest}\n"
                            f"Type: User Account\n\n"
                            "Next steps:\n"
                            "/status - to see and manage tasks\n"
                            "Or /add_user_config - to create more configs"
                        )
                        del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error creating config: {e}")
                        await event.respond(MessageFormatter.format_error_message(str(e)))
                        del pending_auth[user_id]
            
            # ========== BOT CONFIG FLOW ==========
            elif auth_type == "bot_config":
                
                # STEP 1: Collect source channel
                if step == "source":
                    pending_auth[user_id]["source_channel"] = message_text
                    pending_auth[user_id]["step"] = "dest"
                    
                    await event.respond(
                        f"âœ… Source: {message_text}\n\n"
                        "ðŸ“¢ STEP 2/2: Enter DESTINATION channel\n"
                        "(Channel to forward messages TO)\n\n"
                        "Enter channel username or ID:\n"
                        "â€¢ @channel_name\n"
                        "â€¢ -1001234567890\n\n"
                        "Example: @my_archive"
                    )
                
                # STEP 2: Collect destination and create config
                elif step == "dest":
                    try:
                        source = pending_auth[user_id].get("source_channel")
                        dest = message_text
                        
                        if not source:
                            await event.respond("âŒ Error: Source channel lost")
                            del pending_auth[user_id]
                            return
                        
                        config_id = await db.create_config(
                            user_id, source, dest, "bot_account"
                        )
                        
                        await event.respond(
                            f"âœ… Configuration Created!\n\n"
                            f"Config ID: {config_id}\n"
                            f"From: {source}\n"
                            f"To: {dest}\n"
                            f"Type: Bot Account\n\n"
                            "Next steps:\n"
                            "/status - to see and manage tasks\n"
                            "Or /add_bot_config - to create more configs"
                        )
                        del pending_auth[user_id]
                    except Exception as e:
                        logger.error(f"Error creating config: {e}")
                        await event.respond(MessageFormatter.format_error_message(str(e)))
                        del pending_auth[user_id]
        
        except Exception as e:
            logger.error(f"Error in message handler: {e}")                                             
