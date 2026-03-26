from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    env: str = Field("development", env="ENV")
    database_url: str = Field(..., env="DATABASE_URL")

    openai_api_key: str = Field("", env="OPENAI_API_KEY")
    openai_model: str = Field("gpt-3.5-turbo", env="OPENAI_MODEL")

    google_client_id: str = Field("", env="GOOGLE_CLIENT_ID")
    google_client_secret: str = Field("", env="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field("", env="GOOGLE_REDIRECT_URI")
    google_scopes: str = Field(
        "https://www.googleapis.com/auth/calendar "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/userinfo.email "
        "https://www.googleapis.com/auth/userinfo.profile "
        "openid",
        env="GOOGLE_SCOPES",
    )

    jwt_secret: str = Field("troque-esta-chave", env="JWT_SECRET")
    jwt_expires_minutes: int = Field(43200, env="JWT_EXPIRES_MINUTES")

    default_timezone: str = Field("America/Sao_Paulo", env="DEFAULT_TIMEZONE")
    enable_scheduler: bool = Field(False, env="ENABLE_SCHEDULER")
    summary_hour: int = Field(18, env="SUMMARY_HOUR")
    summary_minute: int = Field(0, env="SUMMARY_MINUTE")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def google_scopes_list(self):
        return [s for s in self.google_scopes.split(" ") if s.strip()]


settings = Settings()
