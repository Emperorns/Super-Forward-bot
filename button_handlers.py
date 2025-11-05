from telethon import events
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging
from message_formatter import MessageFormatter

logger = logging.getLogger(__name__)

def setup_button_handlers(bot_client, clients, db, task_manager):
    
    @bot_client.on(events.CallbackQuery(pattern='status'))
    async def status_button_handler(event):
        try:
            tasks = await db.get_active_tasks()
            message = MessageFormatter.format_task_list(tasks)
            
            # Build keyboard
            buttons = []
            for task in tasks:
                task_id = task["_id"]
                config_id = task["config_id"]
                status = task["status"]
                
                if status == "RUNNING":
                    buttons.append([
                        InlineKeyboardButton(f"â¸ï¸ Pause", callback_data=f"pause_{task_id}"),
                        InlineKeyboardButton(f"â¹ï¸ Stop", callback_data=f"stop_{task_id}")
                    ])
                elif status == "PAUSED":
                    buttons.append([
                        InlineKeyboardButton(f"â–¶ï¸ Resume", callback_data=f"resume_{task_id}"),
                        InlineKeyboardButton(f"â¹ï¸ Stop", callback_data=f"stop_{task_id}")
                    ])
            
            buttons.append([
                InlineKeyboardButton("ðŸ”„ Refresh", callback_data="status"),
                InlineKeyboardButton("âž• New Task", callback_data="manage")
            ])
            
            keyboard = InlineKeyboardMarkup(buttons)
            await event.edit(message, buttons=keyboard)
            await event.answer()
        except Exception as e:
            logger.error(f"Error in status button: {e}")
            await event.answer(f"Error: {e}", alert=True)
    
    @bot_client.on(events.CallbackQuery(pattern='manage'))
    async def manage_button_handler(event):
        try:
            configs = await db.get_configs(event.sender_id)
            message = MessageFormatter.format_config_list(configs)
            
            buttons = []
            for config in configs:
                config_id = config["_id"]
                buttons.append([
                    InlineKeyboardButton(f"â–¶ï¸ Start", callback_data=f"start_{config_id}"),
                    InlineKeyboardButton(f"ðŸ—‘ï¸ Delete", callback_data=f"delete_config_{config_id}")
                ])
            
            buttons.append([
                InlineKeyboardButton("ðŸ”™ Back", callback_data="status")
            ])
            
            keyboard = InlineKeyboardMarkup(buttons)
            await event.edit(message, buttons=keyboard)
            await event.answer()
        except Exception as e:
            logger.error(f"Error in manage button: {e}")
            await event.answer(f"Error: {e}", alert=True)
    
    @bot_client.on(events.CallbackQuery(pattern=r'pause_'))
    async def pause_button_handler(event):
        try:
            task_id = event.data.decode().split('_')[1]
            await task_manager.pause_task(task_id)
            
            task = await db.get_task(task_id)
            message = MessageFormatter.format_task_status(task)
            
            buttons = [
                [InlineKeyboardButton("â–¶ï¸ Resume", callback_data=f"resume_{task_id}")],
                [InlineKeyboardButton("ðŸ”„ Refresh", callback_data="status")]
            ]
            
            keyboard = InlineKeyboardMarkup(buttons)
            await event.edit(message, buttons=keyboard)
            await event.answer("Task paused âœ…")
        except Exception as e:
            logger.error(f"Error pausing task: {e}")
            await event.answer(f"Error: {e}", alert=True)
    
    @bot_client.on(events.CallbackQuery(pattern=r'resume_'))
    async def resume_button_handler(event):
        try:
            task_id = event.data.decode().split('_')[1]
            await task_manager.resume_task(task_id)
            
            task = await db.get_task(task_id)
            message = MessageFormatter.format_task_status(task)
            
            buttons = [
                [InlineKeyboardButton("â¸ï¸ Pause", callback_data=f"pause_{task_id}")],
                [InlineKeyboardButton("ðŸ”„ Refresh", callback_data="status")]
            ]
            
            keyboard = InlineKeyboardMarkup(buttons)
            await event.edit(message, buttons=keyboard)
            await event.answer("Task resumed âœ…")
        except Exception as e:
            logger.error(f"Error resuming task: {e}")
            await event.answer(f"Error: {e}", alert=True)
    
    @bot_client.on(events.CallbackQuery(pattern=r'stop_'))
    async def stop_button_handler(event):
        try:
            task_id = event.data.decode().split('_')[1]
            await task_manager.stop_task(task_id)
            
            await event.edit("Task stopped âœ…")
            await event.answer()
        except Exception as e:
            logger.error(f"Error stopping task: {e}")
            await event.answer(f"Error: {e}", alert=True)
    
    @bot_client.on(events.CallbackQuery(pattern=r'delete_'))
    async def delete_button_handler(event):
        try:
            callback_data = event.data.decode()
            
            if callback_data.startswith('delete_task_'):
                task_id = callback_data.split('_')[2]
                await task_manager.delete_task(task_id)
                await event.edit("Task deleted âœ…")
            elif callback_data.startswith('delete_config_'):
                config_id = callback_data.split('_')[2]
                await db.delete_config(config_id)
                await event.edit("Config deleted âœ…")
            
            await event.answer()
        except Exception as e:
            logger.error(f"Error deleting: {e}")
            await event.answer(f"Error: {e}", alert=True)
    
    @bot_client.on(events.CallbackQuery(pattern=r'start_'))
    async def start_forward_button_handler(event):
        try:
            config_id = event.data.decode().split('_')[1]
            
            # Ask for task type
            buttons = [
                [
                    InlineKeyboardButton("ðŸ“Œ Live (Upcoming)", callback_data=f"type_live_{config_id}"),
                    InlineKeyboardButton("ðŸ“š Complete (All)", callback_data=f"type_complete_{config_id}")
                ]
            ]
            
            keyboard = InlineKeyboardMarkup(buttons)
            await event.edit(
                "Choose forwarding type:\n"
                "ðŸ“Œ Live - Forward only new messages\n"
                "ðŸ“š Complete - Forward all existing messages",
                buttons=keyboard
            )
            await event.answer()
        except Exception as e:
            logger.error(f"Error starting forward: {e}")
            await event.answer(f"Error: {e}", alert=True)
    
    @bot_client.on(events.CallbackQuery(pattern=r'type_'))
    async def task_type_button_handler(event):
        try:
            data = event.data.decode().split('_')
            task_type = data[1]
            config_id = data[2]
            
            task_id = await task_manager.start_forward_task(config_id, task_type)
            
            task = await db.get_task(task_id)
            message = MessageFormatter.format_task_status(task)
            
            buttons = [
                [InlineKeyboardButton("â¸ï¸ Pause", callback_data=f"pause_{task_id}")],
                [InlineKeyboardButton("ðŸ”„ Refresh", callback_data="status")]
            ]
            
            keyboard = InlineKeyboardMarkup(buttons)
            await event.edit(message, buttons=keyboard)
            await event.answer("Task started âœ…")
        except Exception as e:
            logger.error(f"Error starting task type: {e}")
            await event.answer(f"Error: {e}", alert=True)
