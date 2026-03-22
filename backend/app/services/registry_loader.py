"""Bootstrap the Service Registry from config or dev defaults."""

from __future__ import annotations

import json
import os

from app.config import Config
from app.services.service_registry import RegionalEndpoint, registry


def load_registry() -> None:
    """
    Load regional endpoints from a JSON config file.

    Expected JSON format::

        [
          {
            "region_key": "MH-MUM",
            "db_url": "mysql+pymysql://...",
            "tier": "Local",
            "display_name": "Mumbai Municipal Corporation"
          }
        ]

    Falls back to registering a single DEV-LOCAL endpoint when no
    config file exists (development / single-region mode).
    """
    config_path = getattr(Config, "REGISTRY_CONFIG_PATH", "")

    if config_path and os.path.isfile(config_path):
        with open(config_path) as fh:
            for entry in json.load(fh):
                registry.register(RegionalEndpoint(**entry))
        return

    # Fallback: register the single local DB for development
    registry.register(
        RegionalEndpoint(
            region_key="IN-DEV",
            db_url=Config.MYSQL_URL,
            tier="Local",
            display_name="Dev Local Database",
        )
    )
