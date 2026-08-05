from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="FebGrid", validation_alias="APP_NAME")
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/febgrid",
        validation_alias="DATABASE_URL",
    )
    database_pool_size: int = Field(default=5, validation_alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=5, validation_alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout_seconds: int = Field(default=10, validation_alias="DATABASE_POOL_TIMEOUT_SECONDS")
    database_pool_recycle_seconds: int = Field(default=300, validation_alias="DATABASE_POOL_RECYCLE_SECONDS")
    cors_origins: str = Field(default="http://localhost:5173", validation_alias="CORS_ORIGINS")
    public_app_url: str = Field(default="http://localhost:5173", validation_alias="PUBLIC_APP_URL")
    supabase_url: str = Field(default="", validation_alias="SUPABASE_URL")
    supabase_anon_key: SecretStr | None = Field(default=None, validation_alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: SecretStr | None = Field(default=None, validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_auth_timeout_seconds: int = Field(default=10, validation_alias="SUPABASE_AUTH_TIMEOUT_SECONDS")
    supabase_storage_bucket: str = Field(default="work-files", validation_alias="SUPABASE_STORAGE_BUCKET")
    supabase_storage_timeout_seconds: int = Field(default=30, validation_alias="SUPABASE_STORAGE_TIMEOUT_SECONDS")
    ai_provider: str = Field(default="mock", validation_alias="AI_PROVIDER")
    ai_provider_mode: str = Field(default="mock", validation_alias="AI_PROVIDER_MODE")
    ai_external_processing_enabled: bool = Field(default=False, validation_alias="AI_EXTERNAL_PROCESSING_ENABLED")
    groq_api_key: SecretStr | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.3-70b-versatile", validation_alias="GROQ_MODEL")
    groq_base_url: str = Field(default="", validation_alias="GROQ_BASE_URL")
    groq_timeout_seconds: int = Field(default=30, validation_alias="GROQ_TIMEOUT_SECONDS")
    groq_max_retries: int = Field(default=2, validation_alias="GROQ_MAX_RETRIES")
    groq_max_input_chars: int = Field(default=12_000, validation_alias="GROQ_MAX_INPUT_CHARS")
    ai_default_temperature: float = Field(default=0.2, validation_alias="AI_DEFAULT_TEMPERATURE")
    ai_default_max_tokens: int = Field(default=800, validation_alias="AI_DEFAULT_MAX_TOKENS")
    ai_job_worker_enabled: bool = Field(default=True, validation_alias="AI_JOB_WORKER_ENABLED")
    ai_job_worker_poll_seconds: float = Field(default=2.0, validation_alias="AI_JOB_WORKER_POLL_SECONDS")
    ai_job_lease_seconds: int = Field(default=600, validation_alias="AI_JOB_LEASE_SECONDS")
    java_bulk_invite_base_url: str = Field(default="", validation_alias="JAVA_BULK_INVITE_BASE_URL")
    java_bulk_invite_service_key: SecretStr | None = Field(default=None, validation_alias="JAVA_BULK_INVITE_SERVICE_KEY")
    java_bulk_invite_timeout_seconds: int = Field(default=20, validation_alias="JAVA_BULK_INVITE_TIMEOUT_SECONDS")
    bulk_invite_max_rows: int = Field(default=500, validation_alias="BULK_INVITE_MAX_ROWS")
    bulk_invite_max_file_bytes: int = Field(default=2_097_152, validation_alias="BULK_INVITE_MAX_FILE_BYTES")
    jwt_secret_key: SecretStr | None = Field(default=None, validation_alias="JWT_SECRET_KEY")

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
