import asyncio
from datetime import datetime
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self, clients, db):
        self.clients = clients
        self.db = db
        self.active_tasks = {}
    
    async def initialize(self):
        """Initialize task manager"""
        logger.info("Task manager initialized")
    
    async def resume_tasks(self):
        """Resume interrupted tasks"""
        try:
            active_tasks = await self.db.get_active_tasks()
            
            for task in active_tasks:
                if task["status"] == "RUNNING":
                    logger.info(f"Resuming task: {task['_id']}")
                    await self.start_task_directly(task)
        
        except Exception as e:
            logger.error(f"Error resuming tasks: {e}")
    
    async def start_forward_task_direct(self, source_channel, dest_channel, auth_method, task_type, user_id):
        """Start forwarding task directly from source and destination"""
        try:
            # Create task in DB
            task_id = await self.db.create_task(source_channel, dest_channel, auth_method, task_type, user_id)
            
            self.active_tasks[task_id] = {
                "source": source_channel,
                "dest": dest_channel,
                "type": task_type,
                "status": "RUNNING"
            }
            
            # Get appropriate client
            if auth_method == "user_account":
                client = self.clients.user_client
            else:
                client = self.clients.telegram_bot
            
            if not client:
                raise Exception(f"Client not available for {auth_method}")
            
            # Start forwarding in background
            if task_type == "complete":
                from forwarder import ForwardingEngine
                engine = ForwardingEngine(client, auth_method, self.db)
                asyncio.create_task(engine.forward_all_messages(source_channel, dest_channel, task_id))
            else:
                from forwarder import ForwardingEngine
                engine = ForwardingEngine(client, auth_method, self.db)
                asyncio.create_task(engine.forward_live_messages(source_channel, dest_channel, task_id))
            
            logger.info(f"Task started: {task_id} ({task_type})")
            return task_id
        
        except Exception as e:
            logger.error(f"Error starting task: {e}")
            raise
    
    async def start_task_directly(self, task):
        """Resume a task from DB"""
        try:
            task_id = task.get("_id")
            source = task.get("source_channel")
            dest = task.get("dest_channel")
            auth_method = task.get("auth_method")
            task_type = task.get("type")
            
            if auth_method == "user_account":
                client = self.clients.user_client
            else:
                client = self.clients.telegram_bot
            
            if not client:
                logger.warning(f"Client not available for {auth_method}")
                return
            
            if task_type == "complete":
                from forwarder import ForwardingEngine
                engine = ForwardingEngine(client, auth_method, self.db)
                asyncio.create_task(engine.forward_all_messages(source, dest, task_id))
            else:
                from forwarder import ForwardingEngine
                engine = ForwardingEngine(client, auth_method, self.db)
                asyncio.create_task(engine.forward_live_messages(source, dest, task_id))
            
            logger.info(f"Task resumed: {task_id}")
        
        except Exception as e:
            logger.error(f"Error resuming task: {e}")
    
    async def pause_task(self, task_id):
        """Pause a running task"""
        try:
            await self.db.update_task_status(task_id, "PAUSED")
            logger.info(f"Task paused: {task_id}")
        except Exception as e:
            logger.error(f"Error pausing task: {e}")
    
    async def resume_task(self, task_id):
        """Resume a paused task"""
        try:
            await self.db.update_task_status(task_id, "RUNNING")
            logger.info(f"Task resumed: {task_id}")
        except Exception as e:
            logger.error(f"Error resuming task: {e}")
    
    async def stop_task(self, task_id):
        """Stop a task"""
        try:
            await self.db.update_task_status(task_id, "STOPPED")
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            logger.info(f"Task stopped: {task_id}")
        except Exception as e:
            logger.error(f"Error stopping task: {e}")
    
    async def delete_task(self, task_id):
        """Delete a task"""
        try:
            await self.db.update_task_status(task_id, "DELETED")
            if task_id in self.active_tasks:
                del self.active_tasks[task_id]
            logger.info(f"Task deleted: {task_id}")
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
    
    async def get_task_status(self, task_id):
        """Get task status"""
        try:
            task = await self.db.get_task(task_id)
            return task
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return None
    
    async def pause_all_tasks(self):
        """Pause all running tasks"""
        try:
            active_tasks = await self.db.get_active_tasks()
            for task in active_tasks:
                if task["status"] == "RUNNING":
                    await self.pause_task(task["_id"])
            logger.info("All tasks paused")
        except Exception as e:
            logger.error(f"Error pausing all tasks: {e}")                
