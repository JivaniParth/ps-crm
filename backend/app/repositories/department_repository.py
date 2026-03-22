from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4

from app.config import Config
from app.repositories.sql_repository import get_sql_store


@dataclass
class Department:
    id: str
    name: str
    description: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
        }


class InMemoryDepartmentRepository:
    def __init__(self) -> None:
        self._store: dict[str, Department] = {}
        self._lock = Lock()
        self._seed_default_departments()

    def _seed_default_departments(self) -> None:
        default_departments = [
            ("Roads", "Road maintenance and repair"),
            ("Water", "Water supply and drainage"),
            ("Electricity", "Power supply and street lighting"),
            ("Sanitation", "Waste management and cleanliness"),
            ("General Grievance", "Other complaints and issues"),
        ]
        for name, description in default_departments:
            self._store[name] = Department(id=str(uuid4()), name=name, description=description)

    def list_all(self) -> list[Department]:
        with self._lock:
            return list(self._store.values())

    def get_by_name(self, name: str) -> Department | None:
        return self._store.get(name)

    def create(self, name: str, description: str = "") -> Department:
        with self._lock:
            if name in self._store:
                raise ValueError(f"Department {name} already exists")
            dept = Department(id=str(uuid4()), name=name, description=description)
            self._store[name] = dept
            return dept

    def update(self, name: str, description: str = "") -> Department | None:
        with self._lock:
            if name not in self._store:
                return None
            self._store[name].description = description
            return self._store[name]

    def delete(self, name: str) -> bool:
        with self._lock:
            if name in self._store:
                del self._store[name]
                return True
            return False


class SQLDepartmentRepository:
    def __init__(self, db_url: str) -> None:
        self._store = get_sql_store(db_url)
        self._seed_default_departments()

    def _seed_default_departments(self) -> None:
        default_departments = [
            ("Roads", "Road maintenance and repair"),
            ("Water", "Water supply and drainage"),
            ("Electricity", "Power supply and street lighting"),
            ("Sanitation", "Waste management and cleanliness"),
            ("General Grievance", "Other complaints and issues"),
        ]
        existing = {item.name for item in self._store.list_departments()}
        for name, description in default_departments:
            if name not in existing:
                self._store.create_department(name, description)

    def _to_model(self, row) -> Department:
        return Department(id=row.id, name=row.name, description=row.description or "")

    def list_all(self) -> list[Department]:
        return [self._to_model(row) for row in self._store.list_departments()]

    def get_by_name(self, name: str) -> Department | None:
        row = self._store.get_department_by_name(name)
        if row is None:
            return None
        return self._to_model(row)

    def create(self, name: str, description: str = "") -> Department:
        row = self._store.create_department(name, description)
        return self._to_model(row)

    def update(self, name: str, description: str = "") -> Department | None:
        row = self._store.update_department(name, description)
        if row is None:
            return None
        return self._to_model(row)

    def delete(self, name: str) -> bool:
        return self._store.delete_department(name)


if Config.USE_IN_MEMORY_REPO:
    department_repo = InMemoryDepartmentRepository()
else:
    department_repo = SQLDepartmentRepository(Config.MYSQL_URL)
