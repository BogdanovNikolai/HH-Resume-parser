"""
Пакет `data_manager` содержит логику работы с данными приложения.

Основные компоненты:
    - DataManager: основной класс управления процессом поиска и обработки резюме.
    - ResumeProcessor: класс для форматирования и подготовки данных резюме.
    - SearchEngine: движок поиска резюме через HeadHunter API.
    - TaskTracker: отслеживание прогресса фоновых задач.
    - Exporter: экспорт результатов в Excel или JSON.

Exports:
    data_manager (DataManager): глобальный экземпляр менеджера данных.
    DataManager: класс для управления данными.
    ResumeProcessor: класс для обработки резюме.
    SearchEngine: класс поискового движка.
    TaskTracker: класс для отслеживания задач.
    Exporter: класс для экспорта данных.
"""

from .manager import DataManager

# === Создаем глобальный экземпляр менеджера данных ===
data_manager = DataManager()

# === Экспортируем основные классы и функции ===
from .resume_processor import ResumeProcessor
from .search_engine import SearchEngine
from .task_tracker import TaskTracker
from .exporters import Exporter

__all__ = [
    "data_manager",
    "DataManager",
    "ResumeProcessor",
    "SearchEngine",
    "TaskTracker",
    "Exporter"
]