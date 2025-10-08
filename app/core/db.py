# app/core/db.py
import logging
from typing import AsyncGenerator
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient | None = None
    database = None

    async def connect(self):
        """Connect to MongoDB and ping to check connection."""
        try:
            self.client = AsyncIOMotorClient(settings.MONGO_URI)
            self.database = self.client[settings.MONGO_DB_NAME]
            # Ping to check if connection is successful
            await self.client.admin.command('ping')
            logger.info("Connected to MongoDB successfully")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    async def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")

    def get_collection(self, collection_name: str):
        """Get a specific collection from the database."""
        if self.database is None:
            raise Exception("Database not connected")
        return self.database[collection_name]


# Singleton instance
mongodb = MongoDB()


# Backward compatibility: get_db function for FastAPI dependency injection
async def get_db() -> AsyncGenerator:
    """
    Yield the MongoDB database instance.
    Ensures database is connected before yielding.
    """
    if mongodb.database is None:
        await mongodb.connect()
    yield mongodb.database
