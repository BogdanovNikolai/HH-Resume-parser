"""
data_manager/exporters.py

Модуль содержит класс Exporter — утилиту для экспорта резюме в различные форматы:
- Excel (.xlsx) — основной формат для пользователя.
- JSON (.json) — для API и внутренних нужд.
"""

from typing import List, Dict, Any, Optional
import os
import pandas as pd
import json
from config import log  # <-- наш глобальный логгер
from config import app_config


class Exporter:
    """
    Класс для экспорта данных в различные форматы.

    Методы:
    - export_to_excel() — сохраняет данные в Excel файл.
    - export_to_json() — сохраняет данные в JSON файл.
    """

    def __init__(self, db_session=None):
        """Инициализирует директорию для вывода, если она не существует."""
        self.output_dir = app_config.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
        self.db_session = db_session
        log.info(f"Exporter инициализирован. Путь для экспорта: {self.output_dir}")

    def export_to_excel(self, data: List[Dict[str, Any]], filename: str = "resumes.xlsx") -> str:
        """
        Сохраняет список резюме в формате Excel (.xlsx).
        :param data: Список словарей с данными о резюме.
        :param filename: Имя файла для сохранения.
        :return: Полный путь к файлу.
        """
        if not data:
            raise ValueError("Нет данных для экспорта в Excel")

        try:
            # Гарантируем, что файл будет иметь расширение .xlsx
            if not filename.endswith(".xlsx"):
                filename += ".xlsx"

            full_path = os.path.join(self.output_dir, filename)

            data_dicts = [item.to_dict() if hasattr(item, 'to_dict') else item for item in data]

            # Проверяем доступность директории
            output_dir = os.path.dirname(full_path)
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

            df = pd.DataFrame(data_dicts)
            df.to_excel(full_path, index=False)  # <-- автоматическое определение движка

            log.info(f"[EXPORT] Данные успешно экспортированы в Excel: {full_path}")
            return full_path

        except Exception as e:
            log.error(f"[EXPORT] Ошибка при экспорте в Excel: {e}", exc_info=True)
            raise

    def export_to_json(self, data: List[Dict[str, Any]], filename: str = "resumes.json") -> str:
        """
        Сохраняет список резюме в формате JSON (.json).

        :param data: Список словарей с данными о резюме.
        :param filename: Имя файла для сохранения.
        :return: Полный путь к файлу.
        """
        if not data:
            raise ValueError("Нет данных для экспорта в JSON")

        try:
            full_path = os.path.join(self.output_dir, filename)

            # Сохраняем в JSON с pretty-print
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            log.info(f"[EXPORT] Данные успешно экспортированы в JSON: {full_path}")
            return full_path

        except Exception as e:
            log.error(f"[EXPORT] Ошибка при экспорте в JSON: {e}", exc_info=True)
            raise
        
    def export_task_results(self, task_id: str, format: str = "excel") -> Optional[str]:
        """
        Экспортирует результаты задачи в указанном формате.
        :param task_id: ID задачи
        :param format: формат экспорта ("excel" или "json")
        :return: путь к файлу
        """
        from database.repository import DatabaseRepository
        db_repo = DatabaseRepository(self.db_session)

        resumes = db_repo.load_resumes_by_task(task_id)
        if not resumes:
            log.warning(f"[EXPORT] Нет резюме для задачи {task_id}")
            return None

        filename = f"resumes_output_custom_{task_id}.{format}"
        full_path = os.path.join(self.output_dir, filename)

        if format == "excel":
            return self.export_to_excel(resumes, filename=full_path)
        elif format == "json":
            return self.export_to_json(resumes, filename=full_path)
        else:
            log.error(f"[EXPORT] Неподдерживаемый формат: {format}")
            return None