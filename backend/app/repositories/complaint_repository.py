"""Complaint repository with in-memory and SQL-backed implementations.

Updated for the National Public Grievance Grid with governance tier,
ownership, and regional fields.
"""

from __future__ import annotations

import json
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

    def list_by_tier(self, tier: str) -> list[Complaint]:
        return [c for c in self._store.values() if c.current_tier == tier]

    def update_status(self, ticket_id: str, status: str) -> Complaint | None:
        with self._lock:
            complaint = self._store.get(ticket_id)
            if complaint is None:
                return None
            complaint.status = status
            complaint.updated_at = datetime.now(timezone.utc)
            if status == "Resolved":
                complaint.resolved_at = datetime.now(timezone.utc)
            return complaint

    def update_tier(self, ticket_id: str, current_tier: str) -> Complaint | None:
        with self._lock:
            complaint = self._store.get(ticket_id)
            if complaint is None:
                return None
            complaint.current_tier = current_tier
            complaint.updated_at = datetime.now(timezone.utc)
            return complaint

    def update_department(self, ticket_id: str, department: str) -> Complaint | None:
        with self._lock:
            complaint = self._store.get(ticket_id)
            if complaint is None:
                return None
            complaint.department = department
            complaint.category = department
            complaint.updated_at = datetime.now(timezone.utc)
            return complaint

    def update_ownership(self, ticket_id: str, stakes: list[dict]) -> Complaint | None:
        with self._lock:
            complaint = self._store.get(ticket_id)
            if complaint is None:
                return None
            complaint.ownership_stakes = stakes
            complaint.updated_at = datetime.now(timezone.utc)
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
                # Grievance Grid fields
                "origin_tier": complaint.origin_tier,
                "current_tier": complaint.current_tier,
                "category": complaint.category,
                "sub_category": complaint.sub_category,
                "state_code": complaint.state_code,
                "city_code": complaint.city_code,
                "pincode": complaint.pincode,
                "ownership_json": json.dumps(complaint.ownership_stakes),
                "priority": complaint.priority,
                "sla_deadline": complaint.sla_deadline,
                "updated_at": complaint.updated_at,
                "resolved_at": complaint.resolved_at,
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
            # Grievance Grid fields
            origin_tier=getattr(row, "origin_tier", "Local") or "Local",
            current_tier=getattr(row, "current_tier", "Local") or "Local",
            category=getattr(row, "category", "") or "",
            sub_category=getattr(row, "sub_category", "") or "",
            state_code=getattr(row, "state_code", "") or "",
            city_code=getattr(row, "city_code", "") or "",
            pincode=getattr(row, "pincode", "") or "",
            ownership_stakes=json.loads(getattr(row, "ownership_json", "[]") or "[]"),
            priority=getattr(row, "priority", "Normal") or "Normal",
            sla_deadline=getattr(row, "sla_deadline", None),
            updated_at=getattr(row, "updated_at", None),
            resolved_at=getattr(row, "resolved_at", None),
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

    def list_by_tier(self, tier: str) -> list[Complaint]:
        all_complaints = self.list_all()
        return [c for c in all_complaints if c.current_tier == tier]

    def update_status(self, ticket_id: str, status: str) -> Complaint | None:
        row = self._store.update_complaint_status(ticket_id, status)
        if row is None:
            return None
        return self._to_model(row)

    def update_tier(self, ticket_id: str, current_tier: str) -> Complaint | None:
        row = self._store.update_complaint_tier(
            ticket_id, current_tier, datetime.now(timezone.utc)
        )
        if row is None:
            return None
        return self._to_model(row)

    def update_department(self, ticket_id: str, department: str) -> Complaint | None:
        complaint = self.get(ticket_id)
        if not complaint:
            return None
        complaint.department = department
        complaint.category = department
        complaint.updated_at = datetime.now(timezone.utc)
        self.save(complaint)
        return complaint

    def update_ownership(self, ticket_id: str, stakes: list[dict]) -> Complaint | None:
        row = self._store.update_complaint_ownership(
            ticket_id, json.dumps(stakes), datetime.now(timezone.utc)
        )
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
