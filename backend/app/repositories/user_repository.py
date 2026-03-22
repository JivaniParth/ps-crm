from __future__ import annotations

import hashlib
import hmac
import os
from secrets import token_hex
from dataclasses import dataclass, field
from threading import Lock

from app.config import Config
from app.repositories.sql_repository import (
    deserialize_departments,
    get_sql_store,
    serialize_departments,
)

CITIZEN = "citizen"
OFFICER = "officer"
ADMIN = "admin"
MAYOR = "mayor"


def _hash_password(password: str, salt: str | None = None) -> str:
    use_salt = salt or token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), use_salt.encode("utf-8"), 130000)
    return f"{use_salt}${digest.hex()}"


def _verify_password(stored_hash: str, password: str) -> bool:
    salt, digest = stored_hash.split("$", maxsplit=1)
    computed = _hash_password(password, salt).split("$", maxsplit=1)[1]
    return hmac.compare_digest(digest, computed)


@dataclass
class User:
    username: str
    password_hash: str
    role: str
    display_name: str
    mobile: str = ""
    ward: str = ""
    departments: list[str] = field(default_factory=list)

    def to_public_dict(self) -> dict[str, str]:
        return {
            "username": self.username,
            "role": self.role,
            "display_name": self.display_name,
            "mobile": self.mobile,
            "ward": self.ward,
            "departments": self.departments,
        }


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._store: dict[str, User] = {}
        self._lock = Lock()
        self._seed_default_users()

    def _seed_default_users(self) -> None:
        self._store["admin@pscrm.gov"] = User(
            username="admin@pscrm.gov",
            password_hash=_hash_password(os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "change-admin-password")),
            role=ADMIN,
            display_name="National Admin",
        )
        self._store["mayor@pscrm.gov"] = User(
            username="mayor@pscrm.gov",
            password_hash=_hash_password(os.getenv("MAYOR_BOOTSTRAP_PASSWORD", "change-mayor-password")),
            role=MAYOR,
            display_name="City Mayor",
        )
        self._store["officer.ward12@pscrm.gov"] = User(
            username="officer.ward12@pscrm.gov",
            password_hash=_hash_password(os.getenv("OFFICER_BOOTSTRAP_PASSWORD", "change-officer-password")),
            role=OFFICER,
            display_name="R. Sharma",
            ward="Ward-12",
        )
        self._store["officer.ward19@pscrm.gov"] = User(
            username="officer.ward19@pscrm.gov",
            password_hash=_hash_password(os.getenv("OFFICER_BOOTSTRAP_PASSWORD", "change-officer-password")),
            role=OFFICER,
            display_name="A. Iyer",
            ward="Ward-19",
        )

    def create_citizen(self, username: str, password: str, display_name: str, mobile: str) -> User:
        with self._lock:
            if username in self._store:
                raise ValueError("username already exists")
            user = User(
                username=username,
                password_hash=_hash_password(password),
                role=CITIZEN,
                display_name=display_name,
                mobile=mobile,
            )
            self._store[username] = user
            return user

    def get(self, username: str) -> User | None:
        return self._store.get(username)

    def verify_password(self, username: str, password: str) -> User | None:
        user = self.get(username)
        if user is None:
            return None
        if not _verify_password(user.password_hash, password):
            return None
        return user

    def list_by_role(self, role: str) -> list[User]:
        with self._lock:
            return [user for user in self._store.values() if user.role == role]

    def update_officer(self, username: str, display_name: str = "", ward: str = "", departments: list[str] = None) -> User | None:
        with self._lock:
            user = self._store.get(username)
            if user is None or user.role not in [OFFICER, MAYOR]:
                return None
            if display_name:
                user.display_name = display_name
            if ward:
                user.ward = ward
            if departments is not None:
                user.departments = departments
            return user

    def create_officer(self, username: str, password: str, display_name: str, ward: str, role: str = OFFICER, departments: list[str] = None) -> User:
        with self._lock:
            if username in self._store:
                raise ValueError("username already exists")
            user = User(
                username=username,
                password_hash=_hash_password(password),
                role=role,
                display_name=display_name,
                ward=ward,
                departments=departments or [],
            )
            self._store[username] = user
            return user

    def delete_user(self, username: str) -> bool:
        with self._lock:
            if username in self._store and self._store[username].role in [OFFICER, MAYOR]:
                del self._store[username]
                return True
            return False


class SQLUserRepository:
    def __init__(self, db_url: str) -> None:
        self._store = get_sql_store(db_url)
        self._seed_default_users()

    def _seed_default_users(self) -> None:
        defaults = [
            {
                "username": "admin@pscrm.gov",
                "password": os.getenv("ADMIN_BOOTSTRAP_PASSWORD", "change-admin-password"),
                "role": ADMIN,
                "display_name": "National Admin",
                "mobile": "",
                "ward": "",
                "departments": [],
            },
            {
                "username": "mayor@pscrm.gov",
                "password": os.getenv("MAYOR_BOOTSTRAP_PASSWORD", "change-mayor-password"),
                "role": MAYOR,
                "display_name": "City Mayor",
                "mobile": "",
                "ward": "",
                "departments": [],
            },
            {
                "username": "officer.ward12@pscrm.gov",
                "password": os.getenv("OFFICER_BOOTSTRAP_PASSWORD", "change-officer-password"),
                "role": OFFICER,
                "display_name": "R. Sharma",
                "mobile": "",
                "ward": "Ward-12",
                "departments": [],
            },
            {
                "username": "officer.ward19@pscrm.gov",
                "password": os.getenv("OFFICER_BOOTSTRAP_PASSWORD", "change-officer-password"),
                "role": OFFICER,
                "display_name": "A. Iyer",
                "mobile": "",
                "ward": "Ward-19",
                "departments": [],
            },
        ]

        for item in defaults:
            if self._store.get_user(item["username"]) is None:
                self._store.upsert_user(
                    {
                        "username": item["username"],
                        "password_hash": _hash_password(item["password"]),
                        "role": item["role"],
                        "display_name": item["display_name"],
                        "mobile": item["mobile"],
                        "ward": item["ward"],
                        "departments_json": serialize_departments(item["departments"]),
                    }
                )

    def _to_user(self, row) -> User:
        return User(
            username=row.username,
            password_hash=row.password_hash,
            role=row.role,
            display_name=row.display_name,
            mobile=row.mobile or "",
            ward=row.ward or "",
            departments=deserialize_departments(row.departments_json or "[]"),
        )

    def create_citizen(self, username: str, password: str, display_name: str, mobile: str) -> User:
        if self._store.get_user(username) is not None:
            raise ValueError("username already exists")

        self._store.upsert_user(
            {
                "username": username,
                "password_hash": _hash_password(password),
                "role": CITIZEN,
                "display_name": display_name,
                "mobile": mobile,
                "ward": "",
                "departments_json": "[]",
            }
        )
        row = self._store.get_user(username)
        return self._to_user(row)

    def get(self, username: str) -> User | None:
        row = self._store.get_user(username)
        if row is None:
            return None
        return self._to_user(row)

    def verify_password(self, username: str, password: str) -> User | None:
        user = self.get(username)
        if user is None:
            return None
        if not _verify_password(user.password_hash, password):
            return None
        return user

    def list_by_role(self, role: str) -> list[User]:
        return [self._to_user(row) for row in self._store.list_users_by_role(role)]

    def update_officer(self, username: str, display_name: str = "", ward: str = "", departments: list[str] = None) -> User | None:
        row = self._store.get_user(username)
        if row is None or row.role not in [OFFICER, MAYOR]:
            return None

        next_departments = deserialize_departments(row.departments_json or "[]")
        if departments is not None:
            next_departments = departments

        self._store.upsert_user(
            {
                "username": row.username,
                "password_hash": row.password_hash,
                "role": row.role,
                "display_name": display_name or row.display_name,
                "mobile": row.mobile,
                "ward": ward or row.ward,
                "departments_json": serialize_departments(next_departments),
            }
        )
        updated = self._store.get_user(username)
        return self._to_user(updated)

    def create_officer(self, username: str, password: str, display_name: str, ward: str, role: str = OFFICER, departments: list[str] = None) -> User:
        if self._store.get_user(username) is not None:
            raise ValueError("username already exists")

        self._store.upsert_user(
            {
                "username": username,
                "password_hash": _hash_password(password),
                "role": role,
                "display_name": display_name,
                "mobile": "",
                "ward": ward,
                "departments_json": serialize_departments(departments or []),
            }
        )
        row = self._store.get_user(username)
        return self._to_user(row)

    def delete_user(self, username: str) -> bool:
        return self._store.delete_user(username, roles=[OFFICER, MAYOR])


if Config.USE_IN_MEMORY_REPO:
    user_repo = InMemoryUserRepository()
else:
    user_repo = SQLUserRepository(Config.MYSQL_URL)
