"""Global Index for cross-region search and national analytics.

Uses MongoDB when available, falls back to an in-memory implementation
so the system works without a running Mongo instance.
"""

from __future__ import annotations

from threading import Lock
from typing import Any


class InMemoryGlobalIndex:
    """In-memory fallback for the Global Index."""

    def __init__(self) -> None:
        self._store: dict[str, dict] = {}
        self._lock = Lock()

    # ── Writes ────────────────────────────────────────────────

    def upsert(self, ticket_id: str, doc: dict) -> None:
        with self._lock:
            doc["_id"] = ticket_id
            self._store[ticket_id] = doc

    def update_status(
        self, ticket_id: str, status: str, current_tier: str | None = None, department: str | None = None
    ) -> None:
        with self._lock:
            doc = self._store.get(ticket_id)
            if doc is None:
                return
            doc["status"] = status
            if current_tier:
                doc["current_tier"] = current_tier
            if department:
                doc["department"] = department
                doc["category"] = department

    def delete(self, ticket_id: str) -> None:
        with self._lock:
            self._store.pop(ticket_id, None)

    # ── Reads ─────────────────────────────────────────────────

    def search(
        self, filters: dict, skip: int = 0, limit: int = 50
    ) -> list[dict]:
        results = []
        for doc in self._store.values():
            match = True
            for key, value in filters.items():
                if doc.get(key) != value:
                    match = False
                    break
            if match:
                results.append(doc)
        return results[skip : skip + limit]

    def count(self, filters: dict) -> int:
        return len(self.search(filters, skip=0, limit=999999))

    def get(self, ticket_id: str) -> dict | None:
        return self._store.get(ticket_id)

    def aggregate_by_tier(self) -> list[dict]:
        """Ticket counts grouped by tier and status."""
        buckets: dict[tuple[str, str], int] = {}
        for doc in self._store.values():
            key = (doc.get("current_tier", ""), doc.get("status", ""))
            buckets[key] = buckets.get(key, 0) + 1
        return [
            {"tier": tier, "status": status, "count": count}
            for (tier, status), count in sorted(buckets.items())
        ]

    def search_by_text(self, query: str, limit: int = 50) -> list[dict]:
        """Simple substring search across descriptions and departments."""
        query_lower = query.lower()
        results = []
        for doc in self._store.values():
            if (
                query_lower in doc.get("description", "").lower()
                or query_lower in doc.get("department", "").lower()
                or query_lower in doc.get("category", "").lower()
            ):
                results.append(doc)
                if len(results) >= limit:
                    break
        return results


class MongoGlobalIndex:
    """MongoDB-backed Global Index. Wraps the global_ticket_index collection."""

    def __init__(self, mongo_url: str, db_name: str) -> None:
        from pymongo import MongoClient, ASCENDING, GEOSPHERE  # type: ignore

        self.client = MongoClient(mongo_url)
        self.col = self.client[db_name]["global_ticket_index"]
        self._ensure_indexes(ASCENDING, GEOSPHERE)

    def _ensure_indexes(self, ASCENDING: Any, GEOSPHERE: Any) -> None:
        self.col.create_index([("state_code", ASCENDING), ("status", ASCENDING)])
        self.col.create_index(
            [("current_tier", ASCENDING), ("status", ASCENDING)]
        )
        self.col.create_index([("citizen_mobile", ASCENDING)])
        self.col.create_index(
            [("sla_deadline", ASCENDING), ("status", ASCENDING)]
        )
        self.col.create_index([("department", ASCENDING), ("category", ASCENDING)])

    def upsert(self, ticket_id: str, doc: dict) -> None:
        doc["_id"] = ticket_id
        self.col.replace_one({"_id": ticket_id}, doc, upsert=True)

    def update_status(
        self, ticket_id: str, status: str, current_tier: str | None = None, department: str | None = None
    ) -> None:
        update: dict[str, Any] = {"$set": {"status": status}}
        if current_tier:
            update["$set"]["current_tier"] = current_tier
        if department:
            update["$set"]["department"] = department
            update["$set"]["category"] = department
        self.col.update_one({"_id": ticket_id}, update)

    def delete(self, ticket_id: str) -> None:
        self.col.delete_one({"_id": ticket_id})

    def search(
        self, filters: dict, skip: int = 0, limit: int = 50
    ) -> list[dict]:
        return list(self.col.find(filters).skip(skip).limit(limit))

    def count(self, filters: dict) -> int:
        return self.col.count_documents(filters)

    def get(self, ticket_id: str) -> dict | None:
        return self.col.find_one({"_id": ticket_id})

    def aggregate_by_tier(self) -> list[dict]:
        return list(
            self.col.aggregate(
                [
                    {
                        "$group": {
                            "_id": {"tier": "$current_tier", "status": "$status"},
                            "count": {"$sum": 1},
                        }
                    },
                    {"$sort": {"_id.tier": 1, "_id.status": 1}},
                ]
            )
        )

    def search_by_text(self, query: str, limit: int = 50) -> list[dict]:
        regex = {"$regex": query, "$options": "i"}
        return list(
            self.col.find(
                {"$or": [{"description": regex}, {"department": regex}, {"category": regex}]}
            ).limit(limit)
        )


def _create_global_index() -> InMemoryGlobalIndex | MongoGlobalIndex:
    """Create the appropriate Global Index based on available configuration."""
    from app.config import Config

    mongo_url = getattr(Config, "MONGO_URL", "")
    mongo_db = getattr(Config, "MONGO_DB_NAME", "pscrm")

    if mongo_url and mongo_url != "mongodb://localhost:27017":
        try:
            idx = MongoGlobalIndex(mongo_url, mongo_db)
            return idx
        except Exception:
            pass

    # Fallback to in-memory
    return InMemoryGlobalIndex()


global_index = _create_global_index()
