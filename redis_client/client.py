"""
Модуль `client` содержит реализацию клиента Redis для хранения прогресса фоновых задач.

Класс RedisClient предоставляет методы для:
- инициализации и подключения к Redis,
- сохранения и обновления прогресса задачи,
- получения и удаления данных о задаче.

Classes:
    RedisClient: клиент Redis для работы с данными прогресса задач.
"""

import redis
import logging
from typing import Optional, Dict, Any

# === Внешние зависимости ===
from config import app_config  # Импортируем глобальный экземпляр конфига

# === Логирование ===
logger = logging.getLogger(__name__)


class RedisClient:
    """
    Клиент Redis для хранения состояния фоновых задач.

    Attributes:
        prefix (str): префикс ключей в Redis.
        ttl (int): время жизни ключей в секундах.
        redis_client (StrictRedis): клиент Redis.
    """

    prefix: str = app_config.REDIS_KEY_PREFIX
    ttl: int = app_config.TTL_HOURS * 3600  # Конвертация часов в секунды

    def __init__(self):
        """
        Инициализирует подключение к Redis.

        Поднимает исключение, если не удалось установить соединение.
        """
        try:
            self.redis_client = redis.StrictRedis(
                host=app_config.REDIS_HOST,
                port=app_config.REDIS_PORT,
                db=app_config.REDIS_DB,
                password=app_config.REDIS_PASSWORD or None,
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self.redis_client.ping()
            logger.info("Успешное подключение к Redis.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Не удалось подключиться к Redis: {e}")
            raise

    def _get_key(self, task_id: str) -> str:
        """
        Генерирует ключ для Redis на основе префикса и ID задачи.

        Args:
            task_id (str): уникальный идентификатор задачи.

        Returns:
            str: сформированный ключ для Redis.
        """
        return f"{self.prefix}progress:{task_id}"

    def init_progress(self, task_id: str) -> None:
        """
        Инициализирует начальное состояние прогресса задачи в Redis.

        Args:
            task_id (str): уникальный идентификатор задачи.
        """
        key = self._get_key(task_id)
        initial_data = {
            "step": "hh",
            "total_hh": 0,
            "current_hh": 0,
            "total_ai": 0,
            "current_ai": 0,
            "status": "ожидание",
            "filename": "",
        }
        try:
            self.redis_client.hmset(key, initial_data)
            self.redis_client.expire(key, self.ttl)
            logger.debug(f"Прогресс инициализирован для task_id: {task_id}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации прогресса для task_id {task_id}: {e}")
            raise

    def update_progress(self, task_id: str, field: str, value: Any) -> None:
        """
        Обновляет конкретное поле прогресса задачи в Redis.

        Args:
            task_id (str): уникальный идентификатор задачи.
            field (str): имя поля для обновления.
            value (Any): новое значение поля.
        """
        key = self._get_key(task_id)
        try:
            self.redis_client.hset(key, field, value)
            logger.debug(f"Поле '{field}' обновлено для task_id: {task_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении поля '{field}' для task_id {task_id}: {e}")
            raise

    def get_progress(self, task_id: str) -> Optional[Dict[str, str]]:
        """
        Получает данные прогресса задачи из Redis.

        Args:
            task_id (str): уникальный идентификатор задачи.

        Returns:
            Optional[Dict[str, str]]: словарь с данными прогресса или None, если задача не найдена.
        """
        key = self._get_key(task_id)
        try:
            progress = self.redis_client.hgetall(key)
            if not progress:
                logger.warning(f"Прогресс для task_id {task_id} не найден.")
            return progress
        except Exception as e:
            logger.error(f"Ошибка при получении прогресса для task_id {task_id}: {e}")
            return None

    def increment_progress(self, task_id: str, field: str, delta: int = 1) -> None:
        """
        Увеличивает значение указанного поля прогресса задачи на заданную величину.

        Args:
            task_id (str): уникальный идентификатор задачи.
            field (str): имя поля для увеличения.
            delta (int): величина приращения (по умолчанию 1).
        """
        key = self._get_key(task_id)
        try:
            self.redis_client.hincrby(key, field, delta)
            logger.debug(f"Поле '{field}' увеличено на {delta} для task_id: {task_id}")
        except Exception as e:
            logger.error(f"Ошибка при инкременте поля '{field}' для task_id {task_id}: {e}")
            raise

    def delete_progress(self, task_id: str) -> None:
        """
        Удаляет запись о прогрессе задачи из Redis.

        Args:
            task_id (str): уникальный идентификатор задачи.
        """
        key = self._get_key(task_id)
        try:
            self.redis_client.delete(key)
            logger.debug(f"Прогресс для task_id {task_id} удален.")
        except Exception as e:
            logger.error(f"Ошибка при удалении прогресса для task_id {task_id}: {e}")
            raise