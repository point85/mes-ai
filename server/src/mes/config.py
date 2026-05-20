from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    All env vars are prefixed with MES_ (e.g. MES_DATABASE_URL, MES_AUTH_MODE).
    See ARCHITECTURE.md §12 for the full configuration reference.
    """

    # --- General ---
    PROJECT_NAME: str = "MES AI"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # --- Database (DATA-LAYER) ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/mes_ai"
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # --- Authentication (AUTH) ---
    AUTH_MODE: str = "none"  # "none" | "local" | "oidc" — none disables auth (dev only); local is dev/fallback; oidc for production
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # OIDC settings (used when AUTH_MODE=oidc)
    OIDC_ISSUER: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_SCOPES: str = "openid,profile,email"
    OIDC_ROLE_CLAIM: str = "groups"
    OIDC_REDIRECT_URI: str = ""

    # --- Event Bus (EVENT-BUS) ---
    EVENT_BUS_TYPE: str = "memory"  # "memory" | "redis" | "kafka" | "nats"
    REDIS_URL: str = "redis://localhost:6379"

    # --- Logging (LOG-CONFIG) ---
    LOG_FILE: str = "mes_server.log"
    LOG_LEVEL: str = "WARNING"  # DEBUG | INFO | WARNING | ERROR | CRITICAL
    LOG_MAX_BYTES: int = 10 * 1024 * 1024  # 10 MB per file before rotation
    LOG_BACKUP_COUNT: int = 5  # keep N rotated files
    LOG_TO_CONSOLE: bool = True

    # --- ERP Adapter (ERP-ADAPTER) ---
    # Generic settings shared by SAP / Oracle / other ERP adapters.
    # Plugins overwrite these at runtime from their manifest parameter values.
    ERP_BASE_URL: str = ""
    ERP_AUTH_TYPE: str = "oauth2"  # oauth2 | basic | api_key
    ERP_CLIENT_ID: str = ""
    ERP_CLIENT_SECRET: str = ""
    ERP_TOKEN_URL: str = ""

    # --- WIP Auto-generation (OPS-REQUEST) ---
    ENABLE_WIP_GENERATOR: bool = False

    # --- Plugin system (PLUGIN-MANAGER) ---
    PLUGIN_DIR: str = "plugins/system"
    PLUGIN_USER_DIR: str = "plugins/user"

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
