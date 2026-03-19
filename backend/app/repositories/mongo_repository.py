from __future__ import annotations

from pymongo import MongoClient


class MongoLogRepository:
    def __init__(self, mongo_url: str, db_name: str) -> None:
        self.client = MongoClient(mongo_url)
        self.collection = self.client[db_name]["complaint_logs"]

    def append(self, ticket_id: str, payload: dict) -> None:
        self.collection.insert_one({"ticket_id": ticket_id, **payload})

    def list_by_ticket(self, ticket_id: str) -> list[dict]:
        return list(self.collection.find({"ticket_id": ticket_id}, {"_id": 0}))
