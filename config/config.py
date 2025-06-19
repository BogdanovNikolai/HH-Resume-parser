import os
from typing import Optional, List
from dotenv import load_dotenv

# Загрузка переменных из .env
load_dotenv()

class Config:
    """
    Класс конфигурации проекта.
    Содержит настройки для Redis, API и Flask.
    """
    
    # === Redis Configuration ===
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD")
    REDIS_KEY_PREFIX: str = os.getenv("REDIS_KEY_PREFIX", "hh_app_")

    # === PostgreSQL Configuration ===
    DB_NAME: str = os.getenv("DB_NAME", "HH-Resume-parser_database")
    DB_USER: str = os.getenv("DB_USER", "HH-Resume-parser_user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "12345678")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    
    @classmethod
    def get_hh_tokens(cls) -> dict:
        """Возвращает словарь с токенами HH"""
        return {
            f"CLIENT_ID{i}": os.getenv(f"CLIENT_ID{i}")
            for i in range(1, 10)
            if os.getenv(f"CLIENT_ID{i}")
        }

    @classmethod
    def get_access_tokens(cls) -> List[str]:
        """Возвращает список ACCESS_TOKEN'ов"""
        return [
            os.getenv(f"ACCESS_TOKEN{i}")
            for i in range(1, 10)
            if os.getenv(f"ACCESS_TOKEN{i}")
        ]

    # === DeepSeek API (для оценки резюме) ===
    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY")

    # === Flask App ===
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fallback_secret_key")

    # === Логирование ===
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE")

    # === Директории ===
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", "output")
    AREAS_CACHE_PATH: str = os.getenv("AREAS_CACHE_PATH", "utils/areas_cache.json")

    # === Лимиты и таймауты ===
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "10"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    TTL_HOURS: int = int(os.getenv("TTL_HOURS", "24"))

    @classmethod
    def validate_required(cls):
        """Проверяет наличие обязательных переменных"""
        required_vars = ["SECRET_KEY", "DEEPSEEK_API_KEY"]
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Отсутствуют обязательные переменные: {missing}")

# При инициализации проверяем обязательные поля
Config.validate_required()