from __future__ import annotations

from secrets import token_urlsafe
from threading import Lock

from app.repositories.user_repository import SQLUserRepository, User, user_repo
from app.services.service_registry import registry


class SessionStore:
    def __init__(self) -> None:
        self._store: dict[str, User] = {}
        self._lock = Lock()

    def issue(self, user: User) -> str:
        token = token_urlsafe(32)
        with self._lock:
            self._store[token] = user
        return token

    def get_user(self, token: str) -> User | None:
        return self._store.get(token)

    def revoke(self, token: str) -> None:
        with self._lock:
            self._store.pop(token, None)


sessions = SessionStore()


def parse_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None
    parts = auth_header.split(" ", maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


ADMIN_FALLBACK_REGION = "IN-DEV"
ADMIN_ACCOUNT = "admin@pscrm.gov"


def login(username: str, password: str, region_key: str | None = None) -> User | None:
    """Authenticate a user. 
    If region_key is provided, check against the regional DB.
    Fallback for admin account to the IN-DEV store if region is missing.
    Otherwise default to the module-level user_repo.
    """
    if region_key and registry.has_region(region_key):
        store = registry.get_store(region_key)
        repo = SQLUserRepository.__new__(SQLUserRepository)
        repo._store = store
        return repo.verify_password(username, password)

    if username == ADMIN_ACCOUNT and region_key is None:
        if registry.has_region(ADMIN_FALLBACK_REGION):
            store = registry.get_store(ADMIN_FALLBACK_REGION)
            repo = SQLUserRepository.__new__(SQLUserRepository)
            repo._store = store
            return repo.verify_password(username, password)

    return user_repo.verify_password(username, password)
