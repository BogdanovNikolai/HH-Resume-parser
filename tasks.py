from celery import Celery
import os
from hh.api import findResumes
from utils.excel_writer import append_resumes_to_excel
import json
import time

# Инициализация Celery
celery_app = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Настройки (опционально)
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

def update_progress(task_id, **kwargs):
    """Обновляет прогресс задачи в Redis"""
    r = get_redis_connection()
    data = r.get(f"task:{task_id}")
    if data:
        progress = json.loads(data)
    else:
        progress = {
            "step": "hh",
            "current_hh": 0,
            "total_hh": 0,
            "current_ai": 0,
            "total_ai": 0,
            "status": "ожидание",
            "filename": None,
            "error": None
        }
    for key, value in kwargs.items():
        progress[key] = value
    r.setex(f"task:{task_id}", 3600, json.dumps(progress))  # TTL 1 час

def get_redis_connection():
    import redis
    return redis.StrictRedis(host='localhost', port=6379, db=0)

@celery_app.task(bind=True)
def export_vacancy_task(self, vacancy_id, access_tokens, filename, description_input, deepseek_api_key):
    update_progress(self.request.id, status="запущено", step="hh", filename=filename)

    result = None
    for idx, token in enumerate(access_tokens):
        try:
            result = findResumes(
                f"vacancy:{vacancy_id}",
                access_token=token,
                limit=100,
                progress_callback=lambda current: update_progress_hh(self.request.id, current, 100)
            )
            if result and result.get("items"):
                break
        except Exception as e:
            print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
            continue

    if not result:
        update_progress(self.request.id, status="ошибка")
        return {"status": "error"}

    append_resumes_to_excel(
        result,
        filename=filename,
        description_input=description_input,
        deepseek_api_key=deepseek_api_key
    )

    update_progress(self.request.id, status="готово", filename=filename)
    return {"status": "success", "filename": filename}

@celery_app.task(bind=True)
def search_resume_task(self, keywords, area_id, count, salary_to, description_input, access_tokens, filename, deepseek_api_key):
    update_progress(self.request.id, status="запущено", step="hh", filename=filename)

    queries = [keywords]
    result = None
    for idx, token in enumerate(access_tokens):
        try:
            result = findResumes(
                *queries,
                access_token=token,
                limit=count,
                area_id=area_id,
                salary_to=salary_to,
                progress_callback=lambda current: update_progress_hh(self.request.id, current, count)
            )
            if result and result.get("items"):
                break
        except Exception as e:
            print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
            continue

    if not result:
        update_progress(self.request.id, status="ошибка")
        return {"status": "error"}

    append_resumes_to_excel(
        result,
        filename=filename,
        description_input=description_input,
        deepseek_api_key=deepseek_api_key
    )

    update_progress(self.request.id, status="готово", filename=filename)
    return {"status": "success", "filename": filename}

def update_progress_hh(task_id, current, total):
    r = get_redis_connection()
    data = r.get(f"task:{task_id}")
    progress = json.loads(data) if data else {}
    progress["current_hh"] = current
    progress["total_hh"] = total
    progress["step"] = "hh"
    r.setex(f"task:{task_id}", 3600, json.dumps(progress))