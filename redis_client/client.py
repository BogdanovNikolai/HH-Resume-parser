import redis
import logging
from typing import Optional, Dict, Any

from config import app_config  # Импортируем глобальный экземпляр конфига

# Настройка логгирования
logger = logging.getLogger(__name__)

class RedisClient:
    prefix: str = app_config.REDIS_KEY_PREFIX
    ttl: int = app_config.TTL_HOURS * 3600

    def __init__(self):
        """
        Инициализирует подключение к Redis.
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
        Генерирует ключ для Redis с префиксом.
        """
        return f"{self.prefix}progress:{task_id}"

    def init_progress(self, task_id: str) -> None:
        """
        Инициализирует прогресс в Redis.
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
        Обновляет конкретное поле прогресса в Redis.
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
        Получает прогресс по task_id.
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
        Увеличивает значение поля прогресса на delta.
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
        Удаляет прогресс по task_id.
        """
        key = self._get_key(task_id)
        try:
            self.redis_client.delete(key)
            logger.debug(f"Прогресс для task_id {task_id} удален.")
        except Exception as e:
            logger.error(f"Ошибка при удалении прогресса для task_id {task_id}: {e}")
            raise