import asyncio
from datetime import datetime, timedelta
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
                    config_id = task["config_id"]
                    task_type = task["type"]
                    await self.start_forward_task(config_id, task_type, task["_id"])
        
        except Exception as e:
            logger.error(f"Error resuming tasks: {e}")
    
    async def start_forward_task(self, config_id, task_type, task_id=None):
        """Start a new forwarding task"""
        try:
            config = await self.db.get_config(config_id)
            if not config:
                raise Exception(f"Config not found: {config_id}")
            
            # Create task if not exists
            if not task_id:
                task_id = await self.db.create_task(config_id, task_type)
            
            self.active_tasks[task_id] = {
                "config_id": config_id,
                "type": task_type,
                "status": "RUNNING"
            }
            
            auth_method = config["auth_method"]
            source_channel = config["source_channel"]
            dest_channel = config["dest_channel"]
            
            # Get appropriate client
            if auth_method == "user_account":
                client = self.clients.user_client
            else:
                client = self.clients.bot_client
            
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
            from bson import ObjectId
            await self.db.tasks.delete_one({"_id": ObjectId(task_id)})
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
