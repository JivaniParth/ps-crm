from __future__ import annotations

from datetime import datetime
import json
from threading import Lock
from uuid import uuid4

from sqlalchemy import DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


class Base(DeclarativeBase):
    pass


class ComplaintRow(Base):
    __tablename__ = "complaints"

    ticket_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    citizen_name: Mapped[str] = mapped_column(String(120))
    mobile: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(String(4096))
    department: Mapped[str] = mapped_column(String(64))
    channel: Mapped[str] = mapped_column(String(24))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    ward: Mapped[str] = mapped_column(String(64))
    assigned_officer: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserRow(Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(255), primary_key=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[str] = mapped_column(String(24))
    display_name: Mapped[str] = mapped_column(String(120))
    mobile: Mapped[str] = mapped_column(String(24), default="")
    ward: Mapped[str] = mapped_column(String(64), default="")
    departments_json: Mapped[str] = mapped_column(Text, default="[]")


class DepartmentRow(Base):
    __tablename__ = "departments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(String(512), default="")


class ComplaintLogRow(Base):
    __tablename__ = "complaint_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(String(32))
    message: Mapped[str] = mapped_column(String(1024))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class SQLComplaintRepository:
    def __init__(self, mysql_url: str) -> None:
        self.engine = create_engine(mysql_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)

    def save_row(self, row: ComplaintRow) -> None:
        with Session(self.engine) as session:
            session.merge(row)
            session.commit()

    def list_rows(self) -> list[ComplaintRow]:
        with Session(self.engine) as session:
            return session.query(ComplaintRow).all()


class SQLStore:
    def __init__(self, db_url: str) -> None:
        self.engine = create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)

    # Complaints
    def upsert_complaint(self, payload: dict) -> None:
        with Session(self.engine) as session:
            row = ComplaintRow(**payload)
            session.merge(row)
            session.commit()

    def get_complaint(self, ticket_id: str) -> ComplaintRow | None:
        with Session(self.engine) as session:
            return session.get(ComplaintRow, ticket_id)

    def list_complaints(self) -> list[ComplaintRow]:
        with Session(self.engine) as session:
            return session.query(ComplaintRow).all()

    def list_complaints_by_mobile(self, mobile: str) -> list[ComplaintRow]:
        with Session(self.engine) as session:
            return session.query(ComplaintRow).filter(ComplaintRow.mobile == mobile).all()

    def list_complaints_by_ward(self, ward: str) -> list[ComplaintRow]:
        with Session(self.engine) as session:
            return session.query(ComplaintRow).filter(ComplaintRow.ward == ward).all()

    def update_complaint_status(self, ticket_id: str, status: str) -> ComplaintRow | None:
        with Session(self.engine) as session:
            row = session.get(ComplaintRow, ticket_id)
            if row is None:
                return None
            row.status = status
            session.commit()
            session.refresh(row)
            return row

    def delete_complaint(self, ticket_id: str) -> bool:
        with Session(self.engine) as session:
            row = session.get(ComplaintRow, ticket_id)
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    # Users
    def upsert_user(self, payload: dict) -> None:
        with Session(self.engine) as session:
            row = UserRow(**payload)
            session.merge(row)
            session.commit()

    def get_user(self, username: str) -> UserRow | None:
        with Session(self.engine) as session:
            return session.get(UserRow, username)

    def list_users_by_role(self, role: str) -> list[UserRow]:
        with Session(self.engine) as session:
            return session.query(UserRow).filter(UserRow.role == role).all()

    def delete_user(self, username: str, roles: list[str] | None = None) -> bool:
        with Session(self.engine) as session:
            row = session.get(UserRow, username)
            if row is None:
                return False
            if roles and row.role not in roles:
                return False
            session.delete(row)
            session.commit()
            return True

    # Departments
    def list_departments(self) -> list[DepartmentRow]:
        with Session(self.engine) as session:
            return session.query(DepartmentRow).all()

    def get_department_by_name(self, name: str) -> DepartmentRow | None:
        with Session(self.engine) as session:
            return session.query(DepartmentRow).filter(DepartmentRow.name == name).first()

    def create_department(self, name: str, description: str = "") -> DepartmentRow:
        with Session(self.engine) as session:
            existing = session.query(DepartmentRow).filter(DepartmentRow.name == name).first()
            if existing is not None:
                raise ValueError(f"Department {name} already exists")
            row = DepartmentRow(id=str(uuid4()), name=name, description=description)
            session.add(row)
            session.commit()
            session.refresh(row)
            return row

    def update_department(self, name: str, description: str = "") -> DepartmentRow | None:
        with Session(self.engine) as session:
            row = session.query(DepartmentRow).filter(DepartmentRow.name == name).first()
            if row is None:
                return None
            row.description = description
            session.commit()
            session.refresh(row)
            return row

    def delete_department(self, name: str) -> bool:
        with Session(self.engine) as session:
            row = session.query(DepartmentRow).filter(DepartmentRow.name == name).first()
            if row is None:
                return False
            session.delete(row)
            session.commit()
            return True

    # Logs
    def append_log(self, ticket_id: str, message: str, timestamp: datetime) -> None:
        with Session(self.engine) as session:
            session.add(ComplaintLogRow(ticket_id=ticket_id, message=message, timestamp=timestamp))
            session.commit()

    def list_logs(self, ticket_id: str) -> list[ComplaintLogRow]:
        with Session(self.engine) as session:
            return (
                session.query(ComplaintLogRow)
                .filter(ComplaintLogRow.ticket_id == ticket_id)
                .order_by(ComplaintLogRow.timestamp.asc())
                .all()
            )


_STORES: dict[str, SQLStore] = {}
_STORES_LOCK = Lock()


def get_sql_store(db_url: str) -> SQLStore:
    with _STORES_LOCK:
        store = _STORES.get(db_url)
        if store is None:
            store = SQLStore(db_url)
            _STORES[db_url] = store
        return store


def serialize_departments(values: list[str]) -> str:
    return json.dumps(values)


def deserialize_departments(value: str) -> list[str]:
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return []
