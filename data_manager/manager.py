import json
from typing import Optional, Dict, Any, List
from hh.api import findResumes, get_vacancy_negotiations
from utils.ai_evaluator import evaluate_candidate_match
from data_manager.resume_processor import ResumeProcessor
from data_manager.search_engine import SearchEngine
from data_manager.task_tracker import TaskTracker
from data_manager.exporters import Exporter
from database.repository import DatabaseRepository
from database.session import get_db
from config import app_config, log

class DataManager:
    def __init__(self):
        self.db_session = next(get_db())
        self.db_repo = DatabaseRepository(self.db_session)
        self.resume_processor = ResumeProcessor()
        self.task_tracker = TaskTracker()
        self.search_engine = SearchEngine()
        self.exporter = Exporter(db_session=self.db_session)
        self.areas_list = self._load_areas()
        log.info("DataManager успешно инициализирован.")

    def _load_areas_from_file(self, filename):
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        def flatten(areas_list, res):
            for area in areas_list:
                res.append({"id": area["id"], "name": area["name"]})
                if area.get("areas"):
                    flatten(area["areas"], res)
        result = []
        flatten(data, result)
        return result

    def _load_areas(self):
        return self._load_areas_from_file(app_config.AREAS_CACHE_PATH)

    def start_search_task(self, task_id: str, keywords: Optional[str] = None,
                          vacancy_id: Optional[str] = None, area_ids: Optional[List[str]] = None,
                          limit: int = 100, description_input: Optional[str] = None,
                          salary_to: Optional[int] = None):
        from threading import Thread
        Thread(target=self._run_background_task, args=(task_id,), kwargs={
            "keywords": keywords,
            "vacancy_id": vacancy_id,
            "area_ids": area_ids,
            "limit": limit,
            "description_input": description_input,
            "salary_to": salary_to
        }).start()

    def _run_background_task(self, task_id: str, **kwargs):
        try:
            # --- 1. Создаем запись в таблице tasks ---
            from database.models import Task  # <-- импортируйте модель Task
            task_record = Task(task_id=task_id)
            self.db_session.add(task_record)
            try:
                self.db_session.flush()  # временно отправляем в БД, чтобы проверить FK
            except Exception as e:
                self.db_session.rollback()
                log.warning(f"[TASK] Задача {task_id} уже существует — продолжаем")

            # --- 2. Ваш текущий код ---
            keywords = kwargs.get("keywords")
            vacancy_id = kwargs.get("vacancy_id")
            area_ids = kwargs.get("area_ids") or []
            limit = kwargs.get("limit", 100)
            description_input = kwargs.get("description_input")
            salary_to = kwargs.get("salary_to")

            search_query = vacancy_id if vacancy_id else keywords
            self.task_tracker.update_step(task_id, "hh")
            result = self.search_engine.find_resumes(search_query, area_ids, limit, salary_to)

            if not result or not result.get("items"):
                self.task_tracker.set_status(task_id, "ошибка")
                return

            filename = f"resumes_output_{vacancy_id or 'custom'}_{task_id}.xlsx"
            self.task_tracker.set_filename(task_id, filename)
            self.task_tracker.update_step(task_id, "ai")
            self.task_tracker.set_total_ai(task_id, len(result["items"]))

            processed_resumes = []
            for idx, raw_resume in enumerate(result["items"]):
                match_percent, explanation = evaluate_candidate_match(
                    raw_resume.get("experience", ""), description_input or "", app_config.DEEPSEEK_API_KEY
                )
                processed = self.resume_processor.format_resume(raw_resume, description_input)
                processed["match_percent"] = match_percent
                processed["explanation"] = explanation
                processed_resumes.append(processed)
                self.task_tracker.increment_current_ai(task_id)

            processed_resumes_db = [
                self.resume_processor.to_db_format(resume) for resume in processed_resumes
            ]

            # --- 3. Теперь можно безопасно сохранять резюме ---
            self.db_repo.save_resumes(task_id, processed_resumes_db)

            self.exporter.export_to_excel(processed_resumes, filename=filename)
            self.task_tracker.set_status(task_id, "готово")
        except Exception as e:
            log.error(f"[TASK] Ошибка при выполнении задачи {task_id}: {e}")
            self.task_tracker.set_status(task_id, "ошибка")

    def get_task_progress(self, task_id: str) -> Optional[Dict]:
        return self.task_tracker.get_progress(task_id)

    def get_new_responses(self, vacancy_id: str) -> Optional[Dict]:
        return self.search_engine.get_new_responses(vacancy_id)

    def get_company_vacancies(self) -> Optional[List[Dict]]:
        return self.search_engine.get_company_vacancies()

    def get_resume_limit(self) -> Optional[int]:
        return self.search_engine.get_resume_limit()

    def export_task_results(self, task_id: str, format: str = "excel") -> Optional[str]:
        return self.exporter.export_task_results(task_id, format)

data_manager = DataManager()