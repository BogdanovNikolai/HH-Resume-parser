"""
data_manager/task_tracker.py

Модуль содержит класс TaskTracker — утилиту для управления состоянием задачи
через Redis. Отслеживает прогресс выполнения, статус, шаг и другие метаданные.
"""

from typing import Dict, Any, Optional
from config import log
from redis_client import redis_client


class TaskTracker:
    """
    Класс для отслеживания прогресса и состояния задачи через Redis.

    Методы:
    - init_task() — инициализирует новую задачу.
    - update_step() — изменяет текущий этап задачи.
    - set_status() — устанавливает статус задачи.
    - increment_progress() — увеличивает значение поля прогресса.
    - get_task_info() — получает полную информацию о задаче.
    """

    def __init__(self):
        log.info("TaskTracker успешно инициализирован.")

    def init_task(self, task_id: str) -> None:
        """
        Инициализирует новую задачу в Redis.

        :param task_id: Уникальный идентификатор задачи.
        """
        try:
            redis_client.init_progress(task_id)
            log.info(f"[TRACKER] Задача '{task_id}' инициализирована")
        except Exception as e:
            log.error(f"[TRACKER] Ошибка при инициализации задачи '{task_id}': {e}", exc_info=True)
            raise

    def update_step(self, task_id: str, step: str) -> None:
        """
        Обновляет текущий этап задачи.

        :param task_id: Идентификатор задачи.
        :param step: Название текущего шага (например, 'hh', 'ai', 'db').
        """
        try:
            redis_client.update_progress(task_id, "step", step)
            log.debug(f"[TRACKER] Шаг задачи '{task_id}' обновлён на '{step}'")
        except Exception as e:
            log.warning(f"[TRACKER] Ошибка при обновлении шага задачи '{task_id}': {e}")

    def set_status(self, task_id: str, status: str) -> None:
        """
        Устанавливает статус задачи.

        :param task_id: Идентификатор задачи.
        :param status: Статус ('ожидание', 'в процессе', 'готово', 'ошибка').
        """
        try:
            redis_client.update_progress(task_id, "status", status)
            log.info(f"[TRACKER] Статус задачи '{task_id}' обновлён на '{status}'")
        except Exception as e:
            log.warning(f"[TRACKER] Ошибка при установке статуса задачи '{task_id}': {e}")

    def increment_progress(self, task_id: str, field: str, delta: int = 1) -> None:
        """
        Увеличивает значение указанного поля прогресса.

        :param task_id: Идентификатор задачи.
        :param field: Поле прогресса ('current_hh', 'current_ai').
        :param delta: Значение для увеличения.
        """
        try:
            redis_client.increment_progress(task_id, field, delta)
            log.debug(f"[TRACKER] Прогресс задачи '{task_id}' увеличен на '{delta}' для поля '{field}'")
        except Exception as e:
            log.warning(f"[TRACKER] Ошибка при инкременте прогресса задачи '{task_id}': {e}")

    def get_task_info(self, task_id: str) -> Dict[str, Any]:
        """
        Возвращает полную информацию о задаче.

        :param task_id: Идентификатор задачи.
        :return: Информация о задаче (статус, шаг, прогресс).
        """
        try:
            info = redis_client.get_progress(task_id)
            if not info:
                log.warning(f"[TRACKER] Не найдена информация о задаче '{task_id}'")
                return {}
            return info
        except Exception as e:
            log.error(f"[TRACKER] Ошибка при получении информации о задаче '{task_id}': {e}")
            return {}