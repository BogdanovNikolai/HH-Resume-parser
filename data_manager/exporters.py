"""
data_manager/exporters.py

Модуль содержит класс Exporter — утилиту для экспорта резюме в различные форматы:
- Excel (.xlsx) — основной формат для пользователя.
- JSON (.json) — для API и внутренних нужд.
"""

from typing import List, Dict, Any
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

    def __init__(self):
        """Инициализирует директорию для вывода, если она не существует."""
        self.output_dir = app_config.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
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
            full_path = os.path.join(self.output_dir, filename)

            # Преобразуем список словарей в DataFrame
            df = pd.DataFrame(data)

            # Сохраняем в Excel
            df.to_excel(full_path, index=False)
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