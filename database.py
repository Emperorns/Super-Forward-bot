from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
import logging
from bson import ObjectId

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, mongodb_uri, db_name='forwarder_bot'):
        self.uri = mongodb_uri
        self.db_name = db_name
        self.client = None
        self.db = None
    
    async def connect(self):
        try:
            self.client = AsyncIOMotorClient(self.uri)
            self.db = self.client[self.db_name]
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def close(self):
        if self.client:
            self.client.close()
            logger.info("Database connection closed")

    # Session Management
    async def save_user_session(self, session_data):
        try:
            await self.db.sessions.update_one(
                {"type": "user"},
                {"$set": {"type": "user", "session": session_data, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            logger.info("User session saved")
        except Exception as e:
            logger.error(f"Error saving user session: {e}")
            raise

    async def get_user_session(self):
        try:
            session_doc = await self.db.sessions.find_one({"type": "user"})
            if session_doc:
                return session_doc.get("session")
            return None
        except Exception as e:
            logger.error(f"Error getting user session: {e}")
            return None

    async def session_exists(self, session_type):
        try:
            session = await self.db.sessions.find_one({"type": session_type})
            return session is not None
        except Exception as e:
            logger.error(f"Error checking session: {e}")
            return False

    # Source Channel Management
    async def add_source_channel(self, user_id, channel_identifier):
        try:
            await self.db.source_channels.update_one(
                {"user_id": user_id},
                {"$addToSet": {"channels": channel_identifier}},
                upsert=True
            )
            logger.info(f"Added source channel {channel_identifier} for user {user_id}")
        except Exception as e:
            logger.error(f"Error adding source channel: {e}")
            raise

    async def remove_source_channel(self, user_id, channel_identifier):
        try:
            await self.db.source_channels.update_one(
                {"user_id": user_id},
                {"$pull": {"channels": channel_identifier}}
            )
            logger.info(f"Removed source channel {channel_identifier} for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing source channel: {e}")

    async def get_source_channels(self, user_id):
        try:
            doc = await self.db.source_channels.find_one({"user_id": user_id})
            return doc.get("channels", []) if doc else []
        except Exception as e:
            logger.error(f"Error getting source channels: {e}")
            return []

    # Destination Channel Management
    async def add_dest_channel(self, user_id, channel_identifier):
        try:
            await self.db.dest_channels.update_one(
                {"user_id": user_id},
                {"$addToSet": {"channels": channel_identifier}},
                upsert=True
            )
            logger.info(f"Added dest channel {channel_identifier} for user {user_id}")
        except Exception as e:
            logger.error(f"Error adding dest channel: {e}")
            raise

    async def remove_dest_channel(self, user_id, channel_identifier):
        try:
            await self.db.dest_channels.update_one(
                {"user_id": user_id},
                {"$pull": {"channels": channel_identifier}}
            )
            logger.info(f"Removed dest channel {channel_identifier} for user {user_id}")
        except Exception as e:
            logger.error(f"Error removing dest channel: {e}")

    async def get_dest_channels(self, user_id):
        try:
            doc = await self.db.dest_channels.find_one({"user_id": user_id})
            return doc.get("channels", []) if doc else []
        except Exception as e:
            logger.error(f"Error getting dest channels: {e}")
            return []

    # Task Management
    async def create_task(self, source_channel, dest_channel, auth_method, task_type, user_id):
        try:
            task = {
                "user_id": user_id,
                "source_channel": source_channel,
                "dest_channel": dest_channel,
                "auth_method": auth_method,
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
        try:
            task = await self.db.tasks.find_one({"_id": ObjectId(task_id)})
            if task:
                task["_id"] = str(task["_id"])
            return task
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    async def update_task_progress(self, task_id, forwarded_count, total_messages, last_message_id):
        try:
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
        try:
            await self.db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"status": status, "updated_at": datetime.utcnow()}}
            )
            logger.info(f"Task {task_id} status updated to {status}")
        except Exception as e:
            logger.error(f"Error updating task status: {e}")

    async def add_error_log(self, task_id, error_message):
        try:
            await self.db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$push": {"error_log": {"error": error_message, "timestamp": datetime.utcnow()}}}
            )
        except Exception as e:
            logger.error(f"Error adding to error log: {e}")

    async def get_active_tasks(self):
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

    async def get_user_tasks(self, user_id):
        try:
            tasks = []
            cursor = self.db.tasks.find({"user_id": user_id})
            async for task in cursor:
                task["_id"] = str(task["_id"])
                tasks.append(task)
            return tasks
        except Exception as e:
            logger.error(f"Error getting user tasks: {e}")
            return []

    async def get_last_forwarded_message_id(self, task_id):
        try:
            task = await self.get_task(task_id)
            if task and task.get("progress"):
                return task["progress"].get("last_forwarded_message_id", 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting last forwarded message ID: {e}")
            return 0                        
