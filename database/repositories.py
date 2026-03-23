import logging
from typing import Any, Dict, List, Optional

from database.connection import get_db

logger = logging.getLogger(__name__)


class ChargePointRepository:
    """CRUD operations for charge points."""

    COLLECTION = "charge_points"

    @classmethod
    async def upsert(cls, charge_point_id: str, data: Dict[str, Any]) -> None:
        db = get_db()
        await db[cls.COLLECTION].update_one(
            {"_id": charge_point_id},
            {"$set": data},
            upsert=True,
        )

    @classmethod
    async def update_last_seen(cls, charge_point_id: str) -> None:
        from datetime import datetime, timezone

        db = get_db()
        await db[cls.COLLECTION].update_one(
            {"_id": charge_point_id},
            {"$set": {"last_seen": datetime.now(timezone.utc).isoformat()}},
            upsert=True,
        )

    @classmethod
    async def update_status(
        cls, charge_point_id: str, connector_id: int, status: str
    ) -> None:
        db = get_db()
        await db[cls.COLLECTION].update_one(
            {"_id": charge_point_id},
            {"$set": {f"connectors.{connector_id}.status": status}},
            upsert=True,
        )

    @classmethod
    async def get(cls, charge_point_id: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        return await db[cls.COLLECTION].find_one({"_id": charge_point_id})

    @classmethod
    async def list_all(cls) -> List[Dict[str, Any]]:
        db = get_db()
        cursor = db[cls.COLLECTION].find()
        return await cursor.to_list(length=None)

    @classmethod
    async def delete(cls, charge_point_id: str) -> None:
        db = get_db()
        await db[cls.COLLECTION].delete_one({"_id": charge_point_id})


class TransactionRepository:
    """CRUD operations for transactions."""

    COLLECTION = "transactions"

    @classmethod
    async def create(cls, data: Dict[str, Any]) -> int:
        db = get_db()
        counter = await db["counters"].find_one_and_update(
            {"_id": "transaction_id"},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True,
        )
        transaction_id = counter["seq"]
        await db[cls.COLLECTION].insert_one({"_id": transaction_id, **data})
        logger.info("Transaction created: id=%s", transaction_id)
        return transaction_id

    @classmethod
    async def stop(cls, transaction_id: int, data: Dict[str, Any]) -> None:
        db = get_db()
        await db[cls.COLLECTION].update_one(
            {"_id": transaction_id},
            {"$set": data},
        )

    @classmethod
    async def add_meter_values(
        cls, transaction_id: int, meter_values: List[Any]
    ) -> None:
        db = get_db()
        await db[cls.COLLECTION].update_one(
            {"_id": transaction_id},
            {"$push": {"meter_values": {"$each": meter_values}}},
        )

    @classmethod
    async def get(cls, transaction_id: int) -> Optional[Dict[str, Any]]:
        db = get_db()
        return await db[cls.COLLECTION].find_one({"_id": transaction_id})

    @classmethod
    async def list_all(cls, limit: int = 100) -> List[Dict[str, Any]]:
        db = get_db()
        cursor = db[cls.COLLECTION].find().sort("_id", -1).limit(limit)
        return await cursor.to_list(length=None)

    @classmethod
    async def list_by_charge_point(
        cls, charge_point_id: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        db = get_db()
        cursor = (
            db[cls.COLLECTION]
            .find({"charge_point_id": charge_point_id})
            .sort("_id", -1)
            .limit(limit)
        )
        return await cursor.to_list(length=None)


class IdTagRepository:
    """CRUD operations for ID tags (RFID / authorization tokens)."""

    COLLECTION = "id_tags"

    @classmethod
    async def get(cls, id_tag: str) -> Optional[Dict[str, Any]]:
        db = get_db()
        return await db[cls.COLLECTION].find_one({"_id": id_tag})

    @classmethod
    async def upsert(cls, id_tag: str, data: Dict[str, Any]) -> None:
        db = get_db()
        await db[cls.COLLECTION].update_one(
            {"_id": id_tag},
            {"$set": data},
            upsert=True,
        )

    @classmethod
    async def list_all(cls) -> List[Dict[str, Any]]:
        db = get_db()
        cursor = db[cls.COLLECTION].find()
        return await cursor.to_list(length=None)

    @classmethod
    async def delete(cls, id_tag: str) -> None:
        db = get_db()
        await db[cls.COLLECTION].delete_one({"_id": id_tag})
