import asyncio
import random
from collections import deque
from datetime import datetime, timedelta
from telethon.errors import FloodWaitError
import logging
from config import RATE_LIMITS, MAX_RETRIES

logger = logging.getLogger(__name__)

class RateLimiter:
    def __init__(self, auth_method):
        self.auth_method = auth_method
        self.config = RATE_LIMITS[auth_method]
        self.forwards_this_minute = deque(maxlen=60)
        self.last_backoff_time = None
        self.backoff_multiplier = 1.0
    
    async def record_forward(self):
        """Record a forward attempt"""
        self.forwards_this_minute.append(datetime.now())
    
    def get_forwards_per_minute(self):
        """Get forwards in last minute"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=60)
        return sum(1 for t in self.forwards_this_minute if t > cutoff)
    
    async def wait_before_forward(self):
        """Wait with intelligent rate limiting"""
        try:
            forwards_per_min = self.get_forwards_per_minute()
            max_per_min = self.config["max_forwards_per_minute"]
            
            base_delay = self.config["base_delay"]
            
            # If approaching rate limit, increase delay
            if forwards_per_min > max_per_min * 0.8:
                base_delay *= 1.5
                logger.warning(f"Rate limit approaching for {self.auth_method}: {forwards_per_min}/{max_per_min}")
            
            # Add randomness to avoid detection
            jitter = random.uniform(-0.05, 0.05)
            total_delay = base_delay + jitter
            total_delay = max(self.config["min_delay"], min(total_delay, self.config["max_delay"]))
            
            await asyncio.sleep(total_delay)
            await self.record_forward()
        except Exception as e:
            logger.error(f"Error in rate limiter: {e}")
            await asyncio.sleep(self.config["base_delay"])
    
    async def handle_flood_wait(self, wait_seconds):
        """Handle Telegram flood wait"""
        try:
            logger.warning(f"Rate limited! Waiting {wait_seconds}s for {self.auth_method}")
            await asyncio.sleep(wait_seconds)
            self.backoff_multiplier = 1.0
        except Exception as e:
            logger.error(f"Error handling flood wait: {e}")
    
    async def exponential_backoff(self, attempt):
        """Calculate exponential backoff time"""
        backoff_time = self.config["base_delay"] * (self.config["backoff_multiplier"] ** attempt)
        return min(backoff_time, 300)  # Cap at 5 minutes

class ForwardingEngine:
    def __init__(self, client, auth_method, db):
        self.client = client
        self.auth_method = auth_method
        self.rate_limiter = RateLimiter(auth_method)
        self.db = db
    
    async def forward_message(self, source_channel, dest_channel, message_id):
        """Forward single message with retry logic"""
        for attempt in range(MAX_RETRIES):
            try:
                await self.rate_limiter.wait_before_forward()
                
                result = await self.client.forward_messages(dest_channel, message_id, source_channel)
                logger.debug(f"Message {message_id} forwarded successfully")
                return result
            
            except FloodWaitError as e:
                await self.rate_limiter.handle_flood_wait(e.seconds)
                backoff = await self.rate_limiter.exponential_backoff(attempt)
                logger.warning(f"FloodWait for {self.auth_method}, retrying in {backoff}s")
                await asyncio.sleep(backoff)
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    backoff = await self.rate_limiter.exponential_backoff(attempt)
                    logger.warning(f"Forward failed (attempt {attempt+1}), retrying: {e}")
                    await asyncio.sleep(backoff)
                else:
                    logger.error(f"Forward failed after {MAX_RETRIES} attempts: {e}")
                    raise
        
        return None
    
    async def get_channel_messages(self, channel, limit=None):
        """Get messages from channel"""
        try:
            messages = []
            async for message in self.client.iter_messages(channel, limit=limit, reverse=True):
                if message and message.text:
                    messages.append(message)
            return messages
        except Exception as e:
            logger.error(f"Error getting messages from channel: {e}")
            raise
    
    async def forward_all_messages(self, source_channel, dest_channel, task_id):
        """Forward all existing messages from source to destination"""
        try:
            logger.info(f"Starting complete forward: {source_channel} -> {dest_channel}")
            
            # Get total message count
            messages = await self.get_channel_messages(source_channel)
            total_messages = len(messages)
            
            if total_messages == 0:
                logger.warning(f"No messages to forward from {source_channel}")
                await self.db.update_task_progress(task_id, 0, 0, 0)
                return
            
            await self.db.update_task_progress(task_id, 0, total_messages, 0)
            
            # Get last forwarded message ID to resume
            last_forwarded_id = await self.db.get_last_forwarded_message_id(task_id)
            
            forwarded_count = 0
            for i, message in enumerate(messages):
                try:
                    if message.id <= last_forwarded_id:
                        continue
                    
                    await self.forward_message(source_channel, dest_channel, message.id)
                    forwarded_count += 1
                    
                    # Update progress every PROGRESS_UPDATE_BATCH messages
                    if forwarded_count % 100 == 0:
                        await self.db.update_task_progress(task_id, forwarded_count, total_messages, message.id)
                        logger.info(f"Progress: {forwarded_count}/{total_messages}")
                
                except Exception as e:
                    await self.db.add_error_log(task_id, str(e))
                    logger.error(f"Error forwarding message {message.id}: {e}")
                    continue
            
            # Final update
            await self.db.update_task_progress(task_id, forwarded_count, total_messages, messages[-1].id if messages else 0)
            await self.db.update_task_status(task_id, "COMPLETED")
            logger.info(f"Complete forward finished: {forwarded_count}/{total_messages} messages")
            
        except Exception as e:
            await self.db.add_error_log(task_id, str(e))
            await self.db.update_task_status(task_id, "ERROR")
            logger.error(f"Error in complete forward: {e}")
            raise
    
    async def forward_live_messages(self, source_channel, dest_channel, task_id):
        """Forward upcoming messages from source to destination"""
        try:
            logger.info(f"Starting live forward: {source_channel} -> {dest_channel}")
            
            async for message in self.client.iter_messages(source_channel, min_id=0):
                try:
                    # Check task status
                    task = await self.db.get_task(task_id)
                    if task["status"] == "PAUSED":
                        await asyncio.sleep(5)
                        continue
                    if task["status"] not in ["RUNNING", "PAUSED"]:
                        break
                    
                    if message and message.text:
                        await self.forward_message(source_channel, dest_channel, message.id)
                        await self.db.update_task_progress(task_id, 1, 1, message.id)
                
                except Exception as e:
                    await self.db.add_error_log(task_id, str(e))
                    logger.error(f"Error in live forward: {e}")
                    continue
        
        except Exception as e:
            await self.db.add_error_log(task_id, str(e))
            await self.db.update_task_status(task_id, "ERROR")
            logger.error(f"Live forward error: {e}")
