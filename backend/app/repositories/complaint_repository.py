from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock

from app.config import Config
from app.models.complaint import Complaint
from app.repositories.sql_repository import get_sql_store


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


class SQLComplaintRepositoryAdapter:
    def __init__(self, db_url: str) -> None:
        self._store = get_sql_store(db_url)

    def save(self, complaint: Complaint) -> Complaint:
        self._store.upsert_complaint(
            {
                "ticket_id": complaint.ticket_id,
                "citizen_name": complaint.citizen_name,
                "mobile": complaint.mobile,
                "description": complaint.description,
                "department": complaint.department,
                "channel": complaint.channel,
                "latitude": complaint.latitude,
                "longitude": complaint.longitude,
                "ward": complaint.ward,
                "assigned_officer": complaint.assigned_officer,
                "status": complaint.status,
                "created_at": complaint.created_at,
            }
        )
        return complaint

    def _to_model(self, row) -> Complaint:
        return Complaint(
            ticket_id=row.ticket_id,
            citizen_name=row.citizen_name,
            mobile=row.mobile,
            description=row.description,
            department=row.department,
            channel=row.channel,
            latitude=row.latitude,
            longitude=row.longitude,
            ward=row.ward,
            assigned_officer=row.assigned_officer,
            status=row.status,
            created_at=row.created_at,
        )

    def get(self, ticket_id: str) -> Complaint | None:
        row = self._store.get_complaint(ticket_id)
        if row is None:
            return None
        return self._to_model(row)

    def list_all(self) -> list[Complaint]:
        return [self._to_model(row) for row in self._store.list_complaints()]

    def list_by_mobile(self, mobile: str) -> list[Complaint]:
        return [self._to_model(row) for row in self._store.list_complaints_by_mobile(mobile)]

    def list_by_ward(self, ward: str) -> list[Complaint]:
        return [self._to_model(row) for row in self._store.list_complaints_by_ward(ward)]

    def update_status(self, ticket_id: str, status: str) -> Complaint | None:
        row = self._store.update_complaint_status(ticket_id, status)
        if row is None:
            return None
        return self._to_model(row)

    def delete(self, ticket_id: str) -> bool:
        return self._store.delete_complaint(ticket_id)


class SQLLogRepositoryAdapter:
    def __init__(self, db_url: str) -> None:
        self._store = get_sql_store(db_url)

    def append(self, ticket_id: str, message: str) -> None:
        self._store.append_log(ticket_id, message, datetime.now(timezone.utc))

    def get(self, ticket_id: str) -> list[dict[str, str]]:
        rows = self._store.list_logs(ticket_id)
        return [
            {
                "message": row.message,
                "timestamp": row.timestamp.isoformat(),
            }
            for row in rows
        ]


if Config.USE_IN_MEMORY_REPO:
    complaint_repo = InMemoryComplaintRepository()
    log_repo = InMemoryLogRepository()
else:
    complaint_repo = SQLComplaintRepositoryAdapter(Config.MYSQL_URL)
    log_repo = SQLLogRepositoryAdapter(Config.MYSQL_URL)
