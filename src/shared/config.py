from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Evolution API (gateway padrão)
    evolution_api_url: str = "http://localhost:8080"
    evolution_api_key: str = ""
    evolution_instance: str = "exatabot"

    # Z-API (gateway alternativo)
    zapi_instance_id: str = ""  # ID da instância no painel Z-API
    zapi_token: str = ""  # Token da instância no painel Z-API
    zapi_client_token: str = ""  # Client-Token da conta Z-API (header de auth)

    # Provedor de WhatsApp ativo: "evolution" ou "zapi"
    whatsapp_provider: str = "evolution"

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

    # Redis (Fase 6)
    redis_url: str = "redis://localhost:6379/0"
    session_store_type: str = "memory"  # "memory" | "redis"
    cache_type: str = "memory"  # "memory" | "redis"

    # Alertas (Fase 7)
    subscription_store_type: str = "memory"  # "memory" | "redis"
    notify_check_interval_minutes: int = 15

    # Logs de Mensagens (Fase 8A)
    database_url: str = ""
    message_log_enabled: bool = False

    # Painel Admin e Segurança JWT (Fase 8C)
    admin_username: str = "admin"
    admin_password_hash: str = ""
    jwt_secret_key: str = "exatabot_super_secret_key_change_me"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 120

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
