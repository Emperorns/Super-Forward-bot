from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongodb_uri, db_name='forwarder_bot'):
        self.uri = mongodb_uri
        self.db_name = db_name
        self.client = None
        self.db = None
    
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(self.uri)
            self.db = self.client[self.db_name]
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Database connection closed")
    
    # User Session Management
    async def save_user_session(self, session_data):
        """Save encrypted user session to MongoDB"""
        try:
            await self.db.sessions.update_one(
                {"type": "user"},
                {"$set": {
                    "type": "user",
                    "session": session_data,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
            logger.info("User session saved")
        except Exception as e:
            logger.error(f"Error saving user session: {e}")
            raise
    
    async def get_user_session(self):
        """Get user session from MongoDB"""
        try:
            session_doc = await self.db.sessions.find_one({"type": "user"})
            if session_doc:
                return session_doc.get("session")
            return None
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return None
    
    async def session_exists(self, session_type):
        """Check if session exists"""
        try:
            session = await self.db.sessions.find_one({"type": session_type})
            return session is not None
        except Exception as e:
            logger.error(f"Error checking session: {e}")
            return False
    
    # Bot Session Management
    async def save_bot_session(self, session_data):
        """Save encrypted bot session to MongoDB"""
        try:
            await self.db.sessions.update_one(
                {"type": "bot"},
                {"$set": {
                    "type": "bot",
                    "session": session_data,
                    "updated_at": datetime.utcnow()
                }},
                upsert=True
            )
            logger.info("Bot session saved")
        except Exception as e:
            logger.error(f"Error saving bot session: {e}")
            raise
    
    async def get_bot_session(self):
        """Get bot session from MongoDB"""
        try:
            session_doc = await self.db.sessions.find_one({"type": "bot"})
            if session_doc:
                return session_doc.get("session")
            return None
        except Exception as e:
            logger.error(f"Error getting bot session: {e}")
            return None
    
    # Configuration Management
    async def create_config(self, user_id, source_channel, dest_channel, auth_method, config_name=None):
        """Create forwarding configuration"""
        try:
            config = {
                "user_id": user_id,
                "source_channel": source_channel,
                "dest_channel": dest_channel,
                "auth_method": auth_method,
                "name": config_name or f"{auth_method}_{datetime.now().timestamp()}",
                "active": True,
                "created_at": datetime.utcnow()
            }
            result = await self.db.configs.insert_one(config)
            logger.info(f"Config created: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating config: {e}")
            raise
    
    async def get_configs(self, user_id):
        """Get all configurations for user"""
        try:
            configs = []
            cursor = self.db.configs.find({"user_id": user_id})
            async for config in cursor:
                config["_id"] = str(config["_id"])
                configs.append(config)
            return configs
        except Exception as e:
            logger.error(f"Error getting configs: {e}")
            return []
    
    async def get_config(self, config_id):
        """Get specific configuration"""
        try:
            from bson import ObjectId
            config = await self.db.configs.find_one({"_id": ObjectId(config_id)})
            if config:
                config["_id"] = str(config["_id"])
            return config
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            return None
    
    async def delete_config(self, config_id):
        """Delete configuration"""
        try:
            from bson import ObjectId
            result = await self.db.configs.delete_one({"_id": ObjectId(config_id)})
            logger.info(f"Config deleted: {config_id}")
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting config: {e}")
            return False
    
    # Task Management
    async def create_task(self, config_id, task_type):
        """Create forwarding task"""
        try:
            task = {
                "config_id": config_id,
                "type": task_type,
                "status": "RUNNING",
                "progress": {
                    "total_messages": 0,
                    "forwarded_count": 0,
                    "last_forwarded_message_id": 0,
                    "last_forwarded_at": datetime.utcnow(),
                    "start_time": datetime.utcnow(),
                    "rate_limit_events": 0
                },
                "error_log": [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            result = await self.db.tasks.insert_one(task)
            logger.info(f"Task created: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            raise
    
    async def get_task(self, task_id):
        """Get task details"""
        try:
            from bson import ObjectId
            task = await self.db.tasks.find_one({"_id": ObjectId(task_id)})
            if task:
                task["_id"] = str(task["_id"])
            return task
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None
    
    async def update_task_progress(self, task_id, forwarded_count, total_messages, last_message_id):
        """Update task progress"""
        try:
            from bson import ObjectId
            await self.db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "progress.forwarded_count": forwarded_count,
                    "progress.total_messages": total_messages,
                    "progress.last_forwarded_message_id": last_message_id,
                    "progress.last_forwarded_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }}
            )
        except Exception as e:
            logger.error(f"Error updating task progress: {e}")
    
    async def update_task_status(self, task_id, status):
        """Update task status"""
        try:
            from bson import ObjectId
            await self.db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {
                    "status": status,
                    "updated_at": datetime.utcnow()
                }}
            )
            logger.info(f"Task {task_id} status updated to {status}")
        except Exception as e:
            logger.error(f"Error updating task status: {e}")
    
    async def add_error_log(self, task_id, error_message):
        """Add error to task log"""
        try:
            from bson import ObjectId
            await self.db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$push": {
                    "error_log": {
                        "error": error_message,
                        "timestamp": datetime.utcnow()
                    }
                }}
            )
            logger.warning(f"Error logged for task {task_id}: {error_message}")
        except Exception as e:
            logger.error(f"Error adding to error log: {e}")
    
    async def get_active_tasks(self):
        """Get all active tasks"""
        try:
            tasks = []
            cursor = self.db.tasks.find({"status": {"$in": ["RUNNING", "PAUSED"]}})
            async for task in cursor:
                task["_id"] = str(task["_id"])
                tasks.append(task)
            return tasks
        except Exception as e:
            logger.error(f"Error getting active tasks: {e}")
            return []
    
    async def save_forwarded_message(self, task_id, original_msg_id, forwarded_msg_id):
        """Track forwarded messages"""
        try:
            await self.db.forwarded_messages.insert_one({
                "task_id": task_id,
                "original_message_id": original_msg_id,
                "forwarded_message_id": forwarded_msg_id,
                "forwarded_at": datetime.utcnow()
            })
        except Exception as e:
            logger.error(f"Error saving forwarded message: {e}")
    
    async def get_last_forwarded_message_id(self, task_id):
        """Get last forwarded message ID for resume"""
        try:
            task = await self.get_task(task_id)
            if task and task.get("progress"):
                return task["progress"].get("last_forwarded_message_id", 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting last forwarded message ID: {e}")
            return 0
