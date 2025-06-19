"""
data_manager/manager.py

Модуль содержит основной класс DataManager — прослойку между внешними сервисами,
базой данных и бизнес-логикой приложения. Отвечает за управление задачами поиска
и обработки резюме, а также их сохранение и экспорт.
"""

from typing import Optional, Dict, Any, List
from config import app_config, log
from hh.api import findResumes, get_vacancy_negotiations
from data_manager.resume_processor import ResumeProcessor
from data_manager.task_tracker import TaskTracker
from data_manager.search_engine import SearchEngine
from data_manager.exporters import Exporter
from utils.ai_evaluator import evaluate_candidate_match
from database.repository import DatabaseRepository
from database.session import get_db
from redis_client import redis_client


class DataManager:
    def __init__(self):
        """Инициализирует компоненты менеджера."""
        self.db_session = next(get_db())
        self.db_repo = DatabaseRepository(self.db_session)

        self.resume_processor = ResumeProcessor()
        self.task_tracker = TaskTracker()
        self.search_engine = SearchEngine()
        self.exporter = Exporter()

        log.info("DataManager успешно инициализирован.")

    def start_search_task(self,
                          task_id: str,
                          keywords: Optional[str] = None,
                          vacancy_id: Optional[str] = None,
                          area_id: Optional[str] = None,
                          count: int = 10,
                          salary_to: Optional[int] = None,
                          description_input: Optional[str] = None) -> None:
        """
        Запускает новую задачу поиска и обработки резюме.
        """
        try:
            self.task_tracker.init_task(task_id)
            self.task_tracker.update_step(task_id, "hh")

            if keywords:
                resumes = self.search_engine.search_by_keywords(keywords, area_id, count, salary_to)
            elif vacancy_id:
                resumes = self.search_engine.search_by_vacancy(vacancy_id)
            else:
                raise ValueError("Не указаны ни ключевые слова, ни ID вакансии")

            total_resumes = len(resumes)
            processed_resumes = []

            for idx, raw_resume in enumerate(resumes):
                candidate_exp = raw_resume.get("experience", "")
                match_percent, explanation = evaluate_candidate_match(
                    candidate_exp,
                    description_input,
                    app_config.DEEPSEEK_API_KEY
                )

                processed = self.resume_processor.format_resume(raw_resume, description_input)
                processed["match_percent"] = match_percent
                processed["explanation"] = explanation

                processed_resumes.append(processed)

                redis_client.increment_progress(task_id, "current_hh")
                log.debug(f"[TASK] Обработано {idx + 1}/{total_resumes} резюме")

            # Сохраняем в БД
            self.db_repo.save_resumes(task_id, processed_resumes)
            log.info(f"[TASK] Все резюме сохранены в БД для задачи '{task_id}'")

            # Экспортируем в Excel
            filename = f"{task_id}_resumes.xlsx"
            self.exporter.export_to_excel(processed_resumes, filename=filename)
            redis_client.update_progress(task_id, "filename", filename)

            # Завершаем задачу
            redis_client.update_progress(task_id, "status", "готово")
            log.info(f"[TASK] Задача '{task_id}' успешно завершена")

        except Exception as e:
            log.error(f"[TASK] Ошибка в задаче '{task_id}': {e}", exc_info=True)
            redis_client.update_progress(task_id, "status", "ошибка")
            raise

    def get_task_result(self, task_id: str) -> Dict[str, Any]:
        """Возвращает результат выполненной задачи."""
        result = {
            "task_id": task_id,
            "progress": redis_client.get_task_info(task_id),
            "resumes": [r.to_dict() for r in self.db_repo.load_resumes_by_task(task_id)]
        }
        return result

    def export_task_result(self, task_id: str, file_format: str = "xlsx") -> str:
        """Экспортирует результат задачи в указанный формат."""
        resumes = self.db_repo.load_resumes_by_task(task_id)
        if not resumes:
            raise ValueError(f"Нет данных для экспорта по задаче '{task_id}'")

        filename = f"{task_id}_export.{file_format}"

        if file_format == "xlsx":
            self.exporter.export_to_excel(resumes, filename=filename)
        elif file_format == "json":
            self.exporter.export_to_json(resumes, filename=filename)
        else:
            raise ValueError(f"Неподдерживаемый формат экспорта: {file_format}")

        return filename

    def load_resumes_by_vacancy(self, vacancy_id: str) -> List[Dict[str, Any]]:
        """Загружает ранее сохранённые резюме по ID вакансии."""
        resumes = self.db_repo.load_resumes_by_vacancy(vacancy_id)
        return [r.to_dict() for r in resumes]

    def get_task_progress(self, task_id: str) -> Dict[str, Any]:
        """Возвращает текущий статус и прогресс задачи."""
        return redis_client.get_task_info(task_id)

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Возвращает список всех задач с количеством резюме и статусом."""
        tasks = []
        for task_id in redis_client.get_all_task_ids():
            progress = self.get_task_progress(task_id)
            resume_count = self.db_repo.get_task_resumes_count(task_id)
            tasks.append({
                "task_id": task_id,
                "status": progress.get("status"),
                "step": progress.get("step"),
                "total_hh": progress.get("total_hh"),
                "current_hh": progress.get("current_hh"),
                "total_ai": progress.get("total_ai"),
                "current_ai": progress.get("current_ai"),
                "resume_count": resume_count,
                "filename": progress.get("filename"),
                "created_at": progress.get("created_at")
            })
        return tasks