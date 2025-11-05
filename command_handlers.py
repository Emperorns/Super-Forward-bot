from telethon import events
import logging
from message_formatter import MessageFormatter
from utils import ValidationHelper, ChannelValidator

logger = logging.getLogger(__name__)

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
                "/login_user - Login with user account (phone + 2FA)\n\n"
                "âš™ï¸ CHANNEL MANAGEMENT:\n"
                "/add_source - Add a source channel\n"
                "/add_dest - Add a destination channel\n"
                "/list_channels - List your channels\n"
                "/remove_source - Remove source channel\n"
                "/remove_dest - Remove destination channel\n\n"
                "ðŸ“Š TASKS:\n"
                "/forward - Forward entire channel (complete)\n"
                "/autoforward - Auto-forward new messages (live)\n"
                "/status - Show active tasks\n"
                "/help - Show help\n"
            )
            
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in start handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    # ==================== LOGIN ====================
    
    @bot_client.on(events.NewMessage(pattern='/login_user'))
    async def login_user_handler(event):
        try:
            user_id = event.sender_id
            already_logged = await clients.is_user_logged_in()
            if already_logged:
                await event.respond("âœ… User account already logged in!")
                return
            
            pending_auth[user_id] = {"step": "phone", "type": "user_login", "phone": None, "code": None}
            
            await event.respond(
                "ðŸ“± STEP 1/3: Enter your phone number\n"
                "Format: +91xxxxxxxxxx (with country code)\n\n"
                "Example: +911234567890"
            )
        except Exception as e:
            logger.error(f"Error in login_user handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    # ==================== CHANNEL MANAGEMENT ====================
    
    @bot_client.on(events.NewMessage(pattern='/add_source'))
    async def add_source_handler(event):
        try:
            user_id = event.sender_id
            logged = await clients.is_user_logged_in() or await clients.is_bot_logged_in()
            if not logged:
                await event.respond("âŒ You must be logged in first.\nUse: /login_user")
                return
            
            pending_auth[user_id] = {"step": "source", "type": "add_source"}
            await event.respond(
                "ðŸ“¢ Send SOURCE channel\n"
                "Format:\n"
                "â€¢ @channel_name\n"
                "â€¢ -1001234567890\n\n"
                "Example: @news_channel"
            )
        except Exception as e:
            logger.error(f"Error in add_source handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/add_dest'))
    async def add_dest_handler(event):
        try:
            user_id = event.sender_id
            logged = await clients.is_user_logged_in() or await clients.is_bot_logged_in()
            if not logged:
                await event.respond("âŒ You must be logged in first.\nUse: /login_user")
                return
            
            pending_auth[user_id] = {"step": "dest", "type": "add_dest"}
            await event.respond(
                "ðŸ“¢ Send DESTINATION channel\n"
                "Format:\n"
                "â€¢ @channel_name\n"
                "â€¢ -1001234567890\n\n"
                "Example: @my_archive"
            )
        except Exception as e:
            logger.error(f"Error in add_dest handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/list_channels'))
    async def list_channels_handler(event):
        try:
            user_id = event.sender_id
            sources = await db.get_source_channels(user_id)
            dests = await db.get_dest_channels(user_id)
            
            message = "ðŸ“‹ YOUR CHANNELS:\n\n"
            message += "ðŸ“¥ SOURCE CHANNELS:\n"
            message += "\n".join([f"â€¢ {ch}" for ch in sources]) if sources else "None"
            message += "\n\nðŸ“¤ DESTINATION CHANNELS:\n"
            message += "\n".join([f"â€¢ {ch}" for ch in dests]) if dests else "None"
            
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in list_channels handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/remove_source'))
    async def remove_source_handler(event):
        try:
            user_id = event.sender_id
            sources = await db.get_source_channels(user_id)
            
            if not sources:
                await event.respond("No source channels to remove")
                return
            
            pending_auth[user_id] = {"step": "rm_source", "type": "remove_source"}
            await event.respond(
                "Which source channel to remove?\n\n" +
                "\n".join([f"â€¢ {ch}" for ch in sources]) +
                "\n\nSend exact channel name:"
            )
        except Exception as e:
            logger.error(f"Error in remove_source handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/remove_dest'))
    async def remove_dest_handler(event):
        try:
            user_id = event.sender_id
            dests = await db.get_dest_channels(user_id)
            
            if not dests:
                await event.respond("No destination channels to remove")
                return
            
            pending_auth[user_id] = {"step": "rm_dest", "type": "remove_dest"}
            await event.respond(
                "Which destination channel to remove?\n\n" +
                "\n".join([f"â€¢ {ch}" for ch in dests]) +
                "\n\nSend exact channel name:"
            )
        except Exception as e:
            logger.error(f"Error in remove_dest handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    # ==================== FORWARD & AUTOFORWARD ====================
    
    @bot_client.on(events.NewMessage(pattern='/forward'))
    async def forward_handler(event):
        try:
            user_id = event.sender_id
            dests = await db.get_dest_channels(user_id)
            
            if not dests:
                await event.respond("âŒ No destination channels. Add one:\n/add_dest")
                return
            
            pending_auth[user_id] = {"step": "select_dest", "type": "forward_dest", "dests": dests}
            
            message = "Select DESTINATION channel:\n\n"
            message += "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(dests)])
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in forward handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/autoforward'))
    async def autoforward_handler(event):
        try:
            user_id = event.sender_id
            dests = await db.get_dest_channels(user_id)
            
            if not dests:
                await event.respond("âŒ No destination channels. Add one:\n/add_dest")
                return
            
            pending_auth[user_id] = {"step": "select_dest", "type": "autoforward_dest", "dests": dests}
            
            message = "Select DESTINATION channel:\n\n"
            message += "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(dests)])
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in autoforward handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    @bot_client.on(events.NewMessage(pattern='/status'))
    async def status_handler(event):
        try:
            user_id = event.sender_id
            tasks = await db.get_user_tasks(user_id)
            
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
                "ðŸ” LOGIN:\n"
                "/login_user - Login with phone\n\n"
                "ðŸ“¢ CHANNELS:\n"
                "/add_source - Add source channel\n"
                "/add_dest - Add destination channel\n"
                "/list_channels - Show all channels\n"
                "/remove_source - Remove source\n"
                "/remove_dest - Remove destination\n\n"
                "âš¡ TASKS:\n"
                "/forward - Forward ALL messages\n"
                "/autoforward - Auto-forward NEW messages\n"
                "/status - Show active tasks\n"
            )
            await event.respond(message)
        except Exception as e:
            logger.error(f"Error in help handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))
    
    # ==================== MESSAGE HANDLER (Multi-step) ====================
    
    @bot_client.on(events.NewMessage())
    async def message_handler(event):
        """Handle multi-step flows"""
        try:
            if not event.is_private:
                return
            
            user_id = event.sender_id
            message_text = event.text.strip()
            
            if user_id not in pending_auth:
                return
            
            auth_state = pending_auth[user_id]
            flow_type = auth_state.get("type")
            step = auth_state.get("step")
            
            # ========== USER LOGIN FLOW ==========
            if flow_type == "user_login":
                if step == "phone":
                    success, result = await auth_handler.initiate_user_login(message_text)
                    if success:
                        pending_auth[user_id]["phone"] = message_text
                        pending_auth[user_id]["step"] = "code"
                        await event.respond(
                            "âœ… Code sent to your Telegram!\n\n"
                            "ðŸ“± STEP 2/3: Enter verification code"
                        )
                    else:
                        await event.respond(MessageFormatter.format_error_message(result))
                        del pending_auth[user_id]
                
                elif step == "code":
                    phone = pending_auth[user_id].get("phone")
                    pending_auth[user_id]["code"] = message_text
                    pending_auth[user_id]["step"] = "password"
                    await event.respond(
                        "ðŸ” STEP 3/3: Enter 2FA password\n"
                        "(Type 'skip' if not enabled)"
                    )
                
                elif step == "password":
                    phone = pending_auth[user_id].get("phone")
                    code = pending_auth[user_id].get("code")
                    pwd = None if message_text.lower() == "skip" else message_text
                    
                    success, result = await auth_handler.verify_user_code(phone, code, pwd)
                    if success:
                        await event.respond(f"âœ… {result}")
                    else:
                        await event.respond(MessageFormatter.format_error_message(result))
                    
                    del pending_auth[user_id]
            
            # ========== ADD SOURCE ==========
            elif flow_type == "add_source" and step == "source":
                is_valid, identifier = ChannelValidator.validate_channel_identifier(message_text)
                if is_valid:
                    await db.add_source_channel(user_id, identifier)
                    await event.respond(f"âœ… Source added: {identifier}")
                else:
                    await event.respond(MessageFormatter.format_error_message(identifier))
                del pending_auth[user_id]
            
            # ========== ADD DEST ==========
            elif flow_type == "add_dest" and step == "dest":
                is_valid, identifier = ChannelValidator.validate_channel_identifier(message_text)
                if is_valid:
                    await db.add_dest_channel(user_id, identifier)
                    await event.respond(f"âœ… Destination added: {identifier}")
                else:
                    await event.respond(MessageFormatter.format_error_message(identifier))
                del pending_auth[user_id]
            
            # ========== REMOVE SOURCE ==========
            elif flow_type == "remove_source" and step == "rm_source":
                await db.remove_source_channel(user_id, message_text)
                await event.respond(f"âœ… Removed: {message_text}")
                del pending_auth[user_id]
            
            # ========== REMOVE DEST ==========
            elif flow_type == "remove_dest" and step == "rm_dest":
                await db.remove_dest_channel(user_id, message_text)
                await event.respond(f"âœ… Removed: {message_text}")
                del pending_auth[user_id]
            
            # ========== FORWARD - SELECT DEST ==========
            elif flow_type == "forward_dest" and step == "select_dest":
                dests = pending_auth[user_id].get("dests", [])
                try:
                    idx = int(message_text) - 1
                    if 0 <= idx < len(dests):
                        dest = dests[idx]
                        sources = await db.get_source_channels(user_id)
                        if not sources:
                            await event.respond("âŒ No source channels. Add one:\n/add_source")
                            del pending_auth[user_id]
                            return
                        
                        pending_auth[user_id]["step"] = "select_source"
                        pending_auth[user_id]["dest_channel"] = dest
                        pending_auth[user_id]["sources"] = sources
                        
                        message = f"âœ… Destination: {dest}\n\nSelect SOURCE channel:\n\n"
                        message += "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(sources)])
                        await event.respond(message)
                    else:
                        await event.respond("âŒ Invalid selection")
                except ValueError:
                    await event.respond("âŒ Send number only")
            
            # ========== FORWARD - SELECT SOURCE ==========
            elif flow_type == "forward_dest" and step == "select_source":
                sources = pending_auth[user_id].get("sources", [])
                try:
                    idx = int(message_text) - 1
                    if 0 <= idx < len(sources):
                        source = sources[idx]
                        dest = pending_auth[user_id].get("dest_channel")
                        
                        # Determine auth method (user or bot)
                        user_logged = await clients.is_user_logged_in()
                        auth_method = "user_account" if user_logged else "bot_account"
                        
                        task_id = await task_manager.start_forward_task_direct(
                            source, dest, auth_method, "complete", user_id
                        )
                        
                        await event.respond(
                            f"âœ… Forward task started!\n\n"
                            f"From: {source}\n"
                            f"To: {dest}\n"
                            f"Task ID: {task_id}\n\n"
                            "/status - to monitor"
                        )
                        del pending_auth[user_id]
                    else:
                        await event.respond("âŒ Invalid selection")
                except ValueError:
                    await event.respond("âŒ Send number only")
            
            # ========== AUTOFORWARD - SELECT DEST ==========
            elif flow_type == "autoforward_dest" and step == "select_dest":
                dests = pending_auth[user_id].get("dests", [])
                try:
                    idx = int(message_text) - 1
                    if 0 <= idx < len(dests):
                        dest = dests[idx]
                        sources = await db.get_source_channels(user_id)
                        if not sources:
                            await event.respond("âŒ No source channels. Add one:\n/add_source")
                            del pending_auth[user_id]
                            return
                        
                        pending_auth[user_id]["step"] = "select_source"
                        pending_auth[user_id]["dest_channel"] = dest
                        pending_auth[user_id]["sources"] = sources
                        
                        message = f"âœ… Destination: {dest}\n\nSelect SOURCE channel:\n\n"
                        message += "\n".join([f"{i+1}. {ch}" for i, ch in enumerate(sources)])
                        await event.respond(message)
                    else:
                        await event.respond("âŒ Invalid selection")
                except ValueError:
                    await event.respond("âŒ Send number only")
            
            # ========== AUTOFORWARD - SELECT SOURCE ==========
            elif flow_type == "autoforward_dest" and step == "select_source":
                sources = pending_auth[user_id].get("sources", [])
                try:
                    idx = int(message_text) - 1
                    if 0 <= idx < len(sources):
                        source = sources[idx]
                        dest = pending_auth[user_id].get("dest_channel")
                        
                        # Determine auth method (user or bot)
                        user_logged = await clients.is_user_logged_in()
                        auth_method = "user_account" if user_logged else "bot_account"
                        
                        task_id = await task_manager.start_forward_task_direct(
                            source, dest, auth_method, "live", user_id
                        )
                        
                        await event.respond(
                            f"âœ… Auto-forward task started!\n\n"
                            f"From: {source}\n"
                            f"To: {dest}\n"
                            f"Task ID: {task_id}\n\n"
                            "/status - to monitor"
                        )
                        del pending_auth[user_id]
                    else:
                        await event.respond("âŒ Invalid selection")
                except ValueError:
                    await event.respond("âŒ Send number only")
        
        except Exception as e:
            logger.error(f"Error in message handler: {e}")
            await event.respond(MessageFormatter.format_error_message(str(e)))                         
