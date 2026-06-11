from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Evolution API
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_instance: str = "exatabot"

    # Bot
    bot_name: str = "Ana"
    business_hours_start: int = 8
    business_hours_end: int = 18
    site_base_url: str = "https://www.exataservicos.net"
    cache_ttl_minutes: int = 30
    results_page_size: int = 3
    max_photos_per_property: int = 3

    # LLM (opcional)
    llm_provider: str = "regex"  # "regex" | "openai" | "deepseek"
    openai_api_key: str = ""
    deepseek_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instância global configurada
try:
    settings = Settings()
except Exception:
    # Fallback para testes se as variáveis obrigatórias não estiverem no ambiente
    import os
    os.environ["EVOLUTION_API_KEY"] = "mock_key_for_testing"
    settings = Settings()
