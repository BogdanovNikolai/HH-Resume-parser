from flask import Flask, render_template, request, send_file, jsonify
from hh.api import findResumes, get_manager_id, get_resume_limits, get_new_responses, get_company_vacancies, get_employer_id, get_vacancy_negotiations
from utils.excel_writer import append_resumes_to_excel, save_new_resumes_to_excel
import os
from typing import List, Dict, Any
from threading import Thread
import json
import requests
from config import app_config  # Глобальный объект конфигурации
from redis_client import redis_client  # Единый клиент Redis для прогресса
import uuid

app = Flask(__name__)

# === Загрузка регионов при старте ===
def load_areas_from_file(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return flatten_areas(data)

def flatten_areas(areas_list, result=None):
    if result is None:
        result = []
    for area in areas_list:
        result.append({"id": area["id"], "name": area["name"]})
        if area.get("areas"):
            flatten_areas(area["areas"], result)
    return result

AREAS_LIST = load_areas_from_file(app_config.AREAS_CACHE_PATH)

# === Начало фоновой задачи ===
@app.route('/vacancy/<vacancy_id>/start')
def start_task(vacancy_id):
    task_id = str(uuid.uuid4())
    redis_client.init_progress(task_id)

    thread = Thread(target=background_task, args=(vacancy_id, task_id))
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

# === Фоновая задача ===
def background_task(vacancy_id, task_id):
    try:
        access_tokens = app_config.get_access_tokens()
        if not access_tokens:
            redis_client.update_progress(task_id, "status", "ошибка")
            print("[ERROR] Нет доступных токенов")
            return

        redis_client.update_progress(task_id, "status", "в процессе")
        redis_client.update_progress(task_id, "step", "hh")

        result = None
        for idx, token in enumerate(access_tokens):
            try:
                result = findResumes(f"vacancy:{vacancy_id}", access_token=token, limit=100)
                if result and result.get("items"):
                    print(f"[SUCCESS] Резюме загружены с токеном #{idx + 1}")
                    break
            except Exception as e:
                print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
                continue
        else:
            redis_client.update_progress(task_id, "status", "ошибка")
            print("[ERROR] Не удалось получить резюме ни с одним из токенов")
            return

        filename = f"resumes_output_{vacancy_id}_{task_id}.xlsx"
        redis_client.update_progress(task_id, "filename", filename)
        description_input = ""  # СПРАВОЧНИК
        deepseek_api_key = app_config.DEEPSEEK_API_KEY

        redis_client.update_progress(task_id, "step", "ai")
        redis_client.update_progress(task_id, "total_ai", len(result["items"]))
        append_resumes_to_excel(result, filename=filename, description_input=description_input, deepseek_api_key=deepseek_api_key, task_id=task_id)

        redis_client.update_progress(task_id, "status", "готово")
        print(f"[SUCCESS] Файл '{filename}' успешно сохранён")

    except Exception as e:
        redis_client.update_progress(task_id, "status", "ошибка")
        print(f"[FATAL] Ошибка в фоновой задаче: {e}")

# === Экспорт новых откликов ===
@app.route('/vacancy/<vacancy_id>/export_new')
def export_new_responses(vacancy_id):
    access_tokens = app_config.get_access_tokens()
    if not access_tokens:
        return "Нет доступных токенов", 500

    result = None
    for idx, token in enumerate(access_tokens):
        try:
            result = get_new_responses(vacancy_id, token)
            if result and result.get("items"):
                print(f"[SUCCESS] Новые отклики получены с токеном #{idx + 1}")
                break
        except Exception as e:
            print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
            continue
    else:
        return "Не удалось получить новые отклики", 500

    filename = f"new_resumes_output_{vacancy_id}.xlsx"
    save_new_resumes_to_excel(result["items"], filename=filename)
    return send_file(filename, as_attachment=True)

# === Экспорт по ключевым словам ===
@app.route('/export', methods=['POST'])
def export_resumes():
    keywords = request.form.get('keywords')
    area_id = request.form.get('area')
    count = int(request.form.get('count', '10'))
    salary_to = request.form.get('salary_to')
    description_input = request.form.get('description_input')

    if not keywords:
        return "Не указаны ключевые слова", 400

    access_tokens = app_config.get_access_tokens()
    if not access_tokens:
        return "Нет доступных токенов", 500

    task_id = str(uuid.uuid4())
    redis_client.init_progress(task_id)
    redis_client.update_progress(task_id, "step", "hh")
    redis_client.update_progress(task_id, "total_hh", count)

    thread = Thread(target=background_export_task, args=(task_id, keywords, area_id, count, salary_to, description_input))
    thread.start()

    return render_template('progress.html', task_id=task_id)

# === Фоновая задача для поиска по ключевым словам ===
def background_export_task(task_id, keywords, area_id, count, salary_to, description_input):
    try:
        access_tokens = app_config.get_access_tokens()
        result = None

        for idx, token in enumerate(access_tokens):
            try:
                result = findResumes(
                    keywords,
                    access_token=token,
                    area_id=area_id,
                    limit=count,
                    salary_to=salary_to,
                    progress_callback=lambda _: redis_client.increment_progress(task_id, "current_hh", 1)
                )
                if result and result.get("items"):
                    print(f"[SUCCESS] Резюме найдены с токеном #{idx + 1}")
                    break
            except Exception as e:
                print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
                continue
        else:
            redis_client.update_progress(task_id, "status", "ошибка")
            return

        filename = f"resumes_by_keywords_{task_id}.xlsx"
        redis_client.update_progress(task_id, "filename", filename)
        append_resumes_to_excel(result, description_input=description_input, deepseek_api_key=app_config.DEEPSEEK_API_KEY, filename=filename, task_id=task_id)

        redis_client.update_progress(task_id, "status", "готово")
    except Exception as e:
        print(f"[ERROR] Ошибка в background_export_task: {e}")
        redis_client.update_progress(task_id, "status", "ошибка")

# === Страница с вакансиями ===
@app.route('/vacancies')
def vacancies():
    access_tokens = []
    i = 1
    while True:
        token = os.getenv(f"ACCESS_TOKEN{i}")
        if token:
            access_tokens.append(token)
            i += 1
        else:
            break

    if not access_tokens:
        return "Нет доступных токенов", 500

    result = []
    for idx, token in enumerate(access_tokens):
        try:
            employer_id = get_employer_id(token)
            if not employer_id:
                print(f"[ERROR] Не удалось получить ID работодателя с токеном #{idx + 1}")
                continue

            vacancies_list = get_company_vacancies(token, employer_id)
            if not vacancies_list:
                print(f"[INFO] Нет активных вакансий у аккаунта #{idx + 1}")
                continue

            # Добавляем к каждой вакансии данные об откликах
            enriched_vacancies = []
            for vacancy in vacancies_list:
                stats = get_vacancy_negotiations(token, vacancy["id"])
                enriched_vacancies.append({
                    "vacancy": vacancy,
                    "total_responses": stats["total"],
                    "new_responses": stats["unread"]
                })

            result = enriched_vacancies
            print(f"[SUCCESS] Вакансии загружены с токеном #{idx + 1}")
            break

        except Exception as e:
            print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
            continue
    else:
        return "Не удалось загрузить вакансии", 500

    return render_template('vacancies.html', vacancies=result, error=None)

# === Главная страница ===
@app.route('/')
def index():
    access_tokens = app_config.get_access_tokens()
    if not access_tokens:
        return render_template('index.html', areas=AREAS_LIST, resume_limit=None)

    access_token = access_tokens[0]
    employer_id = "104309"

    try:
        manager_id = get_manager_id(access_token)
        if not manager_id:
            return render_template('index.html', areas=AREAS_LIST, resume_limit=None)

        limits = get_resume_limits(employer_id, manager_id, access_token)
        resume_limit = limits.get("left", {}).get("resume_view", None)
        return render_template('index.html', areas=AREAS_LIST, resume_limit=resume_limit)
    except Exception as e:
        print(f"[ERROR] Ошибка получения лимита: {e}")
        return render_template('index.html', areas=AREAS_LIST, resume_limit=None)

# === Получение лимита резюме ===
@app.route('/api/resume_limit')
def get_limit():
    access_tokens = app_config.get_access_tokens()
    if not access_tokens:
        return jsonify({"limit": None})

    access_token = access_tokens[0]
    employer_id = "104309"

    try:
        manager_id = get_manager_id(access_token)
        if not manager_id:
            return jsonify({"limit": None})

        limits = get_resume_limits(employer_id, manager_id, access_token)
        return jsonify({"limit": limits.get("left", {}).get("resume_view", None)})
    except Exception as e:
        print(f"[ERROR] Ошибка получения лимита: {e}")
        return jsonify({"limit": None})

# === Запуск приложения ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)