"""
Модуль `task_tracker` содержит класс TaskTracker — утилиту для отслеживания прогресса фоновых задач.

Класс использует Redis для хранения состояния задач:
- шаг выполнения
- статус задачи
- количество обработанных резюме
- имя выходного файла

Classes:
    TaskTracker: класс для управления и отслеживания прогресса задач.

Functions:
    Нет функций верхнего уровня.
"""

from typing import Dict, Optional

# Внешние зависимости
from redis_client import redis_client

# Логирование
from config import log


class TaskTracker:
    """
    Класс для отслеживания прогресса фоновых задач.

    Использует Redis через `redis_client` для хранения и обновления состояния задач.
    Поддерживает следующие метрики:
        - step: текущий этап задачи (например, 'hh', 'ai').
        - status: статус задачи ('в процессе', 'готово', 'ошибка').
        - total_ai: общее количество резюме для оценки AI.
        - current_ai: количество уже обработанных резюме.
        - filename: имя выходного файла после экспорта.

    Methods:
        update_step(): обновляет текущий этап задачи.
        set_status(): устанавливает статус задачи.
        set_total_ai(): задаёт общее количество резюме для обработки.
        increment_current_ai(): увеличивает счётчик обработанных резюме.
        set_filename(): сохраняет имя файла с результатами.
        get_progress(): возвращает текущий прогресс задачи.
    """

    def update_step(self, task_id: str, step: str):
        """
        Обновляет текущий этап выполнения задачи.

        Args:
            task_id (str): уникальный идентификатор задачи.
            step (str): этап выполнения ('hh', 'ai' и т.д.).
        """
        redis_client.update_progress(task_id, "step", step)

    def set_status(self, task_id: str, status: str):
        """
        Устанавливает статус задачи.

        Args:
            task_id (str): уникальный идентификатор задачи.
            status (str): новый статус ('в процессе', 'готово', 'ошибка').
        """
        redis_client.update_progress(task_id, "status", status)

    def set_total_ai(self, task_id: str, total_ai: int):
        """
        Задаёт общее количество резюме для оценки AI.

        Args:
            task_id (str): уникальный идентификатор задачи.
            total_ai (int): общее количество резюме.
        """
        redis_client.update_progress(task_id, "total_ai", total_ai)

    def increment_current_ai(self, task_id: str):
        """
        Увеличивает счётчик обработанных резюме на 1.

        Args:
            task_id (str): уникальный идентификатор задачи.
        """
        redis_client.increment_progress(task_id, "current_ai")

    def set_filename(self, task_id: str, filename: str):
        """
        Сохраняет имя выходного файла с результатами.

        Args:
            task_id (str): уникальный идентификатор задачи.
            filename (str): имя файла с результатами.
        """
        redis_client.update_progress(task_id, "filename", filename)

    def get_progress(self, task_id: str) -> Optional[Dict]:
        """
        Возвращает текущий прогресс задачи.

        Args:
            task_id (str): уникальный идентификатор задачи.

        Returns:
            Optional[Dict]: словарь с информацией о прогрессе или None, если задача не найдена.
        """
        return redis_client.get_progress(task_id)