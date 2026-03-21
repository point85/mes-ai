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

    # --- Integration Adapters (P4) ---
    # ERP adapter: "none" | "mock" | vendor plugin ID (e.g. "sap_s4hana", "dynamics365")
    ERP_ADAPTER: str = "none"
    ERP_BASE_URL: str = ""
    ERP_AUTH_TYPE: str = "oauth2"  # "oauth2" | "basic" | "api_key"
    ERP_CLIENT_ID: str = ""
    ERP_CLIENT_SECRET: str = ""
    ERP_TOKEN_URL: str = ""
    ERP_POLL_INTERVAL_SEC: int = 300
    ERP_RETRY_MAX_ATTEMPTS: int = 5
    ERP_RETRY_BACKOFF_SEC: int = 30
    ERP_MOCK_LATENCY_MS: int = 0
    ERP_MOCK_FAILURE_RATE: float = 0.0

    # Equipment adapter: "none" | "mock" | "opcua" | "mqtt" | "modbus" | "rest"
    EQUIP_ADAPTER: str = "none"
    EQUIP_OPCUA_URL: str = ""
    EQUIP_MQTT_BROKER: str = ""
    EQUIP_MQTT_TOPIC_PREFIX: str = "factory"
    EQUIP_MODBUS_HOST: str = ""
    EQUIP_MODBUS_PORT: int = 502
    EQUIP_MOCK_LATENCY_MS: int = 0
    EQUIP_MOCK_FAILURE_RATE: float = 0.0

    # Test equipment adapter: "none" | "mock"
    TEST_EQUIP_ADAPTER: str = "none"

    model_config = SettingsConfigDict(
        env_prefix="MES_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
