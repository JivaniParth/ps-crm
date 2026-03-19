from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, String, create_engine
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
