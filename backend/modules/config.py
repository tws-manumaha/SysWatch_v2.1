"""
SysWatch v2.1 — Centralized Configuration
Loads from environment variables with .env file support.
"""
import os
from pathlib import Path

# Try to load .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    # Search for .env in current dir, parent dirs, and /opt/syswatch
    for search_path in [Path.cwd(), Path.cwd().parent, Path("/opt/syswatch")]:
        env_path = search_path / ".env"
        if env_path.exists():
            load_dotenv(str(env_path))
            break
except ImportError:
    pass


class Config:
    """Application configuration loaded from environment variables."""

    # --- Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", os.urandom(32).hex())
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # --- Database ---
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "syswatch")
    DB_USER = os.getenv("DB_USER", "syswatch")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
    DB_CONNECT_TIMEOUT = int(os.getenv("DB_CONNECT_TIMEOUT", "10"))

    # --- Redis ---
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

    # --- Security ---
    JWT_SECRET = os.getenv("JWT_SECRET", os.urandom(32).hex())
    JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "8"))
    REFRESH_TOKEN_EXPIRY_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRY_DAYS", "7"))
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
    LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", "15"))
    CORS_ORIGINS = [
        o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",")
        if o.strip()
    ] or None  # None = same-origin only

    # --- AI Providers ---
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
    DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
    CLAUDE_BASE_URL = os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com/v1")

    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    GEMINI_BASE_URL = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta")

    AI_PROVIDER_ORDER = [
        p.strip() for p in os.getenv("AI_PROVIDER_ORDER", "deepseek,claude,openai,gemini").split(",")
    ]
    AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "2"))
    AI_TIMEOUT = int(os.getenv("AI_TIMEOUT", "30"))

    # --- Scheduling ---
    ALERT_CHECK_INTERVAL = int(os.getenv("ALERT_CHECK_INTERVAL", "60"))
    HOST_CHECK_INTERVAL = int(os.getenv("HOST_CHECK_INTERVAL", "120"))
    AI_ANALYSIS_INTERVAL = int(os.getenv("AI_ANALYSIS_INTERVAL", "300"))
    SNMP_POLL_INTERVAL = int(os.getenv("SNMP_POLL_INTERVAL", "180"))
    LOG_CLEANUP_INTERVAL = "0 2 * * *"  # daily at 2 AM
    BACKUP_SCHEDULE = os.getenv("BACKUP_SCHEDULE", "0 2 * * *")
    BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "15"))
    BACKUP_DIR = os.getenv("BACKUP_DIR", "/var/backups/syswatch")
    LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "30"))

    # --- SSL / Let's Encrypt ---
    ENABLE_SSL = os.getenv("ENABLE_SSL", "true").lower() == "true"
    SSL_DOMAIN = os.getenv("SSL_DOMAIN", "")
    SSL_EMAIL = os.getenv("SSL_EMAIL", "")
    SSL_CERT_DIR = os.getenv("SSL_CERT_DIR", "/etc/letsencrypt/live")

    # --- Paths ---
    LOG_DIR = os.getenv("LOG_DIR", "/var/log/syswatch")
    APP_DIR = os.getenv("APP_DIR", str(Path(__file__).resolve().parent.parent))

    # --- Encryption ---
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", os.urandom(32).hex())

    # --- Agent ---
    AGENT_REPORT_ENDPOINT = os.getenv("AGENT_REPORT_ENDPOINT", "/api/agent/report")
    AGENT_HEARTBEAT_INTERVAL = int(os.getenv("AGENT_HEARTBEAT_INTERVAL", "60"))

    @classmethod
    def get_db_config(cls) -> dict:
        """Return database connection parameters as a dict."""
        return {
            "host": cls.DB_HOST,
            "port": cls.DB_PORT,
            "database": cls.DB_NAME,
            "user": cls.DB_USER,
            "password": cls.DB_PASSWORD,
            "pool_size": cls.DB_POOL_SIZE,
            "pool_recycle": cls.DB_POOL_RECYCLE,
            "connect_timeout": cls.DB_CONNECT_TIMEOUT,
        }

    @classmethod
    def get_redis_config(cls) -> dict:
        """Return Redis connection parameters as a dict."""
        return {
            "host": cls.REDIS_HOST,
            "port": cls.REDIS_PORT,
            "db": cls.REDIS_DB,
            "password": cls.REDIS_PASSWORD or None,
        }

    @classmethod
    def get_ai_providers(cls) -> list:
        """Return list of configured AI providers in priority order."""
        providers = []
        for name in cls.AI_PROVIDER_ORDER:
            key_attr = f"{name.upper()}_API_KEY"
            model_attr = f"{name.upper()}_MODEL"
            base_attr = f"{name.upper()}_BASE_URL"
            api_key = getattr(cls, key_attr, "")
            if api_key:
                providers.append({
                    "name": name,
                    "api_key": api_key,
                    "model": getattr(cls, model_attr, ""),
                    "base_url": getattr(cls, base_attr, ""),
                })
        return providers

    @classmethod
    def validate(cls) -> list:
        """Return a list of configuration warnings/errors."""
        errors = []
        if not cls.DB_PASSWORD:
            errors.append("DB_PASSWORD is not set")
        if not any([cls.DEEPSEEK_API_KEY, cls.CLAUDE_API_KEY,
                     cls.OPENAI_API_KEY, cls.GEMINI_API_KEY]):
            errors.append("No AI provider API keys configured")
        if cls.ENABLE_SSL and not cls.SSL_DOMAIN:
            errors.append("ENABLE_SSL is true but SSL_DOMAIN is not set")
        if cls.JWT_SECRET == os.urandom(32).hex():
            errors.append("JWT_SECRET is auto-generated (will change on restart)")
        return errors
