"""
Пакет `redis_client` предоставляет клиентский интерфейс для работы с Redis.

Содержит:
    - RedisClient: класс для взаимодействия с Redis.
    - redis_client: глобальный экземпляр клиента Redis.

Exports:
    redis_client: готовый к использованию экземпляр RedisClient.
"""

from .client import RedisClient

# === Глобальный экземпляр клиента Redis ===
redis_client = RedisClient()