from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from app.models.complaint import Complaint


class InMemoryComplaintRepository:
    def __init__(self) -> None:
        self._store: dict[str, Complaint] = {}
        self._lock = Lock()

    def save(self, complaint: Complaint) -> Complaint:
        with self._lock:
            self._store[complaint.ticket_id] = complaint
        return complaint

    def get(self, ticket_id: str) -> Complaint | None:
        return self._store.get(ticket_id)

    def list_all(self) -> list[Complaint]:
        return list(self._store.values())

    def list_by_mobile(self, mobile: str) -> list[Complaint]:
        return [complaint for complaint in self._store.values() if complaint.mobile == mobile]

    def list_by_ward(self, ward: str) -> list[Complaint]:
        return [complaint for complaint in self._store.values() if complaint.ward == ward]

    def update_status(self, ticket_id: str, status: str) -> Complaint | None:
        with self._lock:
            complaint = self._store.get(ticket_id)
            if complaint is None:
                return None
            complaint.status = status
            return complaint

    def delete(self, ticket_id: str) -> bool:
        with self._lock:
            if ticket_id in self._store:
                del self._store[ticket_id]
                return True
            return False


class InMemoryLogRepository:
    def __init__(self) -> None:
        self._logs: dict[str, list[dict[str, str]]] = {}
        self._lock = Lock()

    def append(self, ticket_id: str, message: str) -> None:
        with self._lock:
            entry = {
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._logs.setdefault(ticket_id, []).append(entry)

    def get(self, ticket_id: str) -> list[dict[str, str]]:
        return self._logs.get(ticket_id, [])


complaint_repo = InMemoryComplaintRepository()
log_repo = InMemoryLogRepository()
