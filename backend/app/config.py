import os


class Config:
    APP_NAME = "PSCRM"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

    MYSQL_URL = os.getenv("MYSQL_URL", "sqlite:///pscrm.db")
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "pscrm")

    # Default to persistent SQL storage. Set USE_IN_MEMORY_REPO=true for ephemeral demo mode.
    USE_IN_MEMORY_REPO = os.getenv("USE_IN_MEMORY_REPO", "false").lower() == "true"
