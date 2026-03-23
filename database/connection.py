import logging
from typing import Optional

import motor.motor_asyncio

import config

logger = logging.getLogger(__name__)

_client: Optional[motor.motor_asyncio.AsyncIOMotorClient] = None
_db: Optional[motor.motor_asyncio.AsyncIOMotorDatabase] = None


async def connect_db() -> None:
    """Create a Motor client and connect to MongoDB."""
    global _client, _db
    _client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGO_URI)
    _db = _client[config.MONGO_DB_NAME]
    logger.info("Connected to MongoDB: %s / %s", config.MONGO_URI, config.MONGO_DB_NAME)


async def disconnect_db() -> None:
    """Close the Motor client."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
        logger.info("Disconnected from MongoDB")


def get_db() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Return the active database handle."""
    if _db is None:
        raise RuntimeError("Database is not connected. Call connect_db() first.")
    return _db
