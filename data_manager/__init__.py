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