from flask import Flask, render_template, request, send_file, jsonify
from hh.api import findResumes, get_manager_id, get_resume_limits, get_new_responses, get_company_vacancies, get_employer_id, get_vacancy_negotiations
from utils.excel_writer import save_resumes_to_excel
import os
from threading import Thread
import json
from typing import List, Dict, Any, Optional, Callable
from config import app_config
from redis_client import redis_client
import uuid

app = Flask(__name__)

# === Универсальная функция для выполнения с токеном ===
def execute_with_token(func: Callable[..., Optional[Dict]], *args, **kwargs) -> Optional[Dict]:
    access_tokens = app_config.get_access_tokens()
    if not access_tokens:
        print("[ERROR] Нет доступных токенов")
        return None
    for idx, token in enumerate(access_tokens):
        try:
            result = func(token, *args, **kwargs)
            if result:
                return result
        except Exception as e:
            print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
    return None


# === Загрузка регионов (удалить, если не используется) ===
def load_areas_from_file(filename):
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

AREAS_LIST = load_areas_from_file(app_config.AREAS_CACHE_PATH)


# === Начало фоновой задачи ===
@app.route('/vacancy/<vacancy_id>/start')
def start_task(vacancy_id):
    task_id = str(uuid.uuid4())
    redis_client.init_progress(task_id)
    thread = Thread(target=run_background_task, args=(f"vacancy:{vacancy_id}", task_id, vacancy_id))
    thread.start()
    return jsonify({"task_id": task_id})


# === Получение прогресса ===
@app.route('/progress/<task_id>')
def get_task_progress(task_id):
    progress_data = redis_client.get_progress(task_id)
    if not progress_data:
        return jsonify({"error": "Task not found"}), 404
    step = progress_data.get("step", "hh")
    current = int(progress_data.get(f"current_{step}", 0))
    total = int(progress_data.get(f"total_{step}", 1))
    return jsonify({
        "step": step,
        "percent": round((current / total) * 100) if total else 0,
        "status": progress_data.get("status", "ожидание"),
        "filename": progress_data.get("filename", "")
    })


# === Скачивание файла ===
@app.route('/download/<task_id>')
def download_file(task_id):
    progress_data = redis_client.get_progress(task_id)
    filename = progress_data.get("filename") if progress_data else None
    if filename and os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    return "Файл не найден", 404


# === Универсальная фоновая задача ===
def run_background_task(search_query: str, task_id: str, vacancy_id: str = "", area_id: str = "", limit: int = 100, description_input: str = "", salary_to: Optional[int] = None):
    try:
        redis_client.update_progress(task_id, "status", "в процессе")
        redis_client.update_progress(task_id, "step", "hh")

        result = execute_with_token(
            lambda token: findResumes(search_query, access_token=token, area_id=area_id, limit=limit, salary_to=salary_to,
                                      progress_callback=lambda _: redis_client.increment_progress(task_id, "current_hh", 1))
        )

        if not result or not result.get("items"):
            redis_client.update_progress(task_id, "status", "ошибка")
            return

        filename = f"resumes_output_{vacancy_id}_{task_id}.xlsx"
        redis_client.update_progress(task_id, "filename", filename)
        redis_client.update_progress(task_id, "step", "ai")
        redis_client.update_progress(task_id, "total_ai", len(result["items"]))

        save_resumes_to_excel(
            result["items"],
            filename=filename,
            description_input=description_input,
            deepseek_api_key=app_config.DEEPSEEK_API_KEY,
            task_id=task_id
        )

        redis_client.update_progress(task_id, "status", "готово")
        print(f"[SUCCESS] Файл '{filename}' успешно сохранён")

    except Exception as e:
        redis_client.update_progress(task_id, "status", "ошибка")
        print(f"[FATAL] Ошибка в фоновой задаче: {e}")


# === Экспорт новых откликов ===
@app.route('/vacancy/<vacancy_id>/export_new')
def export_new_responses(vacancy_id):
    result = execute_with_token(lambda token: get_new_responses(vacancy_id, token))
    if not result or not result.get("items"):
        return "Не удалось получить новые отклики", 500

    filename = f"new_resumes_output_{vacancy_id}.xlsx"
    save_resumes_to_excel(result["items"], filename=filename, is_new=True)
    return send_file(filename, as_attachment=True)


# === Экспорт по ключевым словам ===
@app.route('/export', methods=['POST'])
def export_resumes():
    keywords = request.form.get('keywords')
    area_id = request.form.getlist('area')
    count = int(request.form.get('count', '10'))
    salary_to = request.form.get('salary_to')
    description_input = request.form.get('description_input')

    if not keywords:
        return "Не указаны ключевые слова", 400

    task_id = str(uuid.uuid4())
    redis_client.init_progress(task_id)
    redis_client.update_progress(task_id, "step", "hh")
    redis_client.update_progress(task_id, "total_hh", count)

    thread = Thread(target=run_background_task, args=(keywords, task_id, "", area_id, count, description_input, salary_to))
    thread.start()

    return render_template('progress.html', task_id=task_id)


# === Страница с вакансиями ===
@app.route('/vacancies')
def vacancies():
    def fetch_vacancies(token):
        employer_id = get_employer_id(token)
        if not employer_id:
            return None
        vacancies_list = get_company_vacancies(token, employer_id)
        if not vacancies_list:
            return []
        enriched_vacancies = []
        for vacancy in vacancies_list:
            stats = get_vacancy_negotiations(token, vacancy["id"])
            enriched_vacancies.append({
                "vacancy": vacancy,
                "total_responses": stats["total"],
                "new_responses": stats["unread"]
            })
        return enriched_vacancies

    result = execute_with_token(fetch_vacancies)
    if not result:
        return "Не удалось загрузить вакансии", 500

    return render_template('vacancies.html', vacancies=result, error=None)


# === Главная страница ===
@app.route('/')
def index():
    def fetch_limit(token):
        manager_id = get_manager_id(token)
        if not manager_id:
            return None
        employer_id = "104309"
        limits = get_resume_limits(employer_id, manager_id, token)
        return limits.get("left", {}).get("resume_view", None)

    resume_limit = execute_with_token(fetch_limit)
    return render_template('index.html', areas=AREAS_LIST, resume_limit=resume_limit)


# === Получение лимита резюме ===
@app.route('/api/resume_limit')
def get_limit():
    def fetch_limit(token):
        manager_id = get_manager_id(token)
        if not manager_id:
            return None
        employer_id = "104309"
        limits = get_resume_limits(employer_id, manager_id, token)
        return limits.get("left", {}).get("resume_view", None)

    resume_limit = execute_with_token(fetch_limit)
    return jsonify({"limit": resume_limit})


# === Запуск приложения ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)