from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from uuid import uuid4


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


department_repo = InMemoryDepartmentRepository()
