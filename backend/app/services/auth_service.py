from __future__ import annotations

from secrets import token_urlsafe
from threading import Lock

from app.repositories.user_repository import User


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
