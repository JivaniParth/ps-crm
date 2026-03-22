"""Service Registry — maps region keys to database connections."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

from app.repositories.sql_repository import SQLStore


@dataclass(frozen=True)
class RegionalEndpoint:
    """Connection metadata for one regional database."""
    region_key: str            # e.g. "MH-MUM"
    db_url: str                # SQLAlchemy DSN
    tier: str                  # "Local" | "State" | "Central"
    display_name: str          # "Mumbai Municipal Corporation"

    def to_dict(self) -> dict[str, str]:
        return {
            "region_key": self.region_key,
            "tier": self.tier,
            "display_name": self.display_name,
        }


class ServiceRegistry:
    """
    Singleton registry that maps region keys to database connections.
    Loaded from a config file / admin API on boot, hot-reloadable.
    """

    def __init__(self) -> None:
        self._endpoints: dict[str, RegionalEndpoint] = {}
        self._stores: dict[str, SQLStore] = {}
        self._lock = Lock()

    # ── Registration ──────────────────────────────────────────

    def register(self, ep: RegionalEndpoint) -> None:
        with self._lock:
            self._endpoints[ep.region_key] = ep

    def deregister(self, region_key: str) -> None:
        with self._lock:
            self._endpoints.pop(region_key, None)
            self._stores.pop(region_key, None)

    # ── Resolution ────────────────────────────────────────────

    def resolve(self, region_key: str) -> RegionalEndpoint:
        """Resolve a region key to its endpoint metadata."""
        ep = self._endpoints.get(region_key)
        if ep is None:
            raise KeyError(f"No regional endpoint registered for '{region_key}'")
        return ep

    def get_store(self, region_key: str) -> SQLStore:
        """
        Lazy-connect: return an SQLStore for the given region,
        creating the engine only on first access.
        """
        store = self._stores.get(region_key)
        if store is not None:
            return store

        with self._lock:
            # Double-check after acquiring lock
            store = self._stores.get(region_key)
            if store is not None:
                return store

            ep = self.resolve(region_key)
            store = SQLStore(ep.db_url)
            self._stores[region_key] = store
            return store

    def get_default_store(self) -> SQLStore | None:
        """Return the first registered store (for dev/single-region mode)."""
        if not self._endpoints:
            return None
        first_key = next(iter(self._endpoints))
        return self.get_store(first_key)

    # ── Discovery ─────────────────────────────────────────────

    def list_regions(self) -> list[RegionalEndpoint]:
        return list(self._endpoints.values())

    def regions_for_tier(self, tier: str) -> list[RegionalEndpoint]:
        return [ep for ep in self._endpoints.values() if ep.tier == tier]

    def has_region(self, region_key: str) -> bool:
        return region_key in self._endpoints


# Module-level singleton
registry = ServiceRegistry()
