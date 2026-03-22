"""Audit repository for tier-transfer records.

Provides both in-memory and SQL-backed implementations matching the
existing repository pattern in the codebase.
"""

from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Optional

from app.config import Config
from app.models.audit import TierTransferAudit
from app.repositories.sql_repository import get_sql_store


class InMemoryAuditRepository:
    """In-memory store for tier-transfer audit records."""

    def __init__(self) -> None:
        self._store: dict[str, TierTransferAudit] = {}
        self._by_ticket: dict[str, list[str]] = {}
        self._lock = Lock()

    def save(self, audit: TierTransferAudit) -> TierTransferAudit:
        with self._lock:
            self._store[audit.audit_id] = audit
            self._by_ticket.setdefault(audit.ticket_id, []).append(
                audit.audit_id
            )
        return audit

    def get(self, audit_id: str) -> Optional[TierTransferAudit]:
        return self._store.get(audit_id)

    def list_by_ticket(self, ticket_id: str) -> list[TierTransferAudit]:
        ids = self._by_ticket.get(ticket_id, [])
        return [self._store[aid] for aid in ids if aid in self._store]

    def list_by_tier(
        self,
        tier: str = "",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[TierTransferAudit]:
        results = []
        for audit in self._store.values():
            if tier and audit.to_tier != tier and audit.from_tier != tier:
                continue
            if from_date and audit.timestamp < from_date:
                continue
            if to_date and audit.timestamp > to_date:
                continue
            results.append(audit)
        return sorted(results, key=lambda a: a.timestamp)

    def list_all(self) -> list[TierTransferAudit]:
        return sorted(self._store.values(), key=lambda a: a.timestamp)


class SQLAuditRepository:
    """SQL-backed audit repository using SQLStore."""

    def __init__(self, db_url: str) -> None:
        self._store = get_sql_store(db_url)

    def save(self, audit: TierTransferAudit) -> TierTransferAudit:
        self._store.save_audit(audit)
        return audit

    def get(self, audit_id: str) -> Optional[TierTransferAudit]:
        row = self._store.get_audit(audit_id)
        if row is None:
            return None
        return self._to_model(row)

    def list_by_ticket(self, ticket_id: str) -> list[TierTransferAudit]:
        rows = self._store.list_audits_by_ticket(ticket_id)
        return [self._to_model(r) for r in rows]

    def list_by_tier(
        self,
        tier: str = "",
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
    ) -> list[TierTransferAudit]:
        rows = self._store.list_audits_by_tier(tier, from_date, to_date)
        return [self._to_model(r) for r in rows]

    def list_all(self) -> list[TierTransferAudit]:
        rows = self._store.list_all_audits()
        return [self._to_model(r) for r in rows]

    @staticmethod
    def _to_model(row) -> TierTransferAudit:
        import json

        return TierTransferAudit(
            audit_id=row.audit_id,
            ticket_id=row.ticket_id,
            from_tier=row.from_tier,
            to_tier=row.to_tier,
            from_department=row.from_department,
            to_department=row.to_department,
            reason=row.reason,
            initiated_by=row.initiated_by,
            approved_by=row.approved_by or "",
            transfer_type=row.transfer_type or "escalation",
            metadata=json.loads(row.metadata_json or "{}"),
            timestamp=row.timestamp,
            checksum=row.checksum or "",
        )


if Config.USE_IN_MEMORY_REPO:
    audit_repo = InMemoryAuditRepository()
else:
    audit_repo = SQLAuditRepository(Config.MYSQL_URL)
