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

    # --- Plugin Framework (PLUGIN-FW) ---
    PLUGIN_DIR: str = "plugins/system"
    PLUGIN_USER_DIR: str = "plugins/user"

    # --- Event Bus (EVENT-BUS) ---
    EVENT_BUS_TYPE: str = "memory"  # "memory" | "redis" | "kafka" | "nats"
    REDIS_URL: str = "redis://localhost:6379"

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
