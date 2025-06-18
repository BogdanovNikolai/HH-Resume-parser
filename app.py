from flask import Flask, render_template, request, send_file, jsonify
from hh.api import findResumes, get_manager_id, get_resume_limits, get_new_responses
from utils.excel_writer import append_resumes_to_excel, save_new_resumes_to_excel
import os
from typing import List, Dict, Any, Optional
from threading import Thread, Lock
from progress import progress_lock, global_progress
import json
import requests

app = Flask(__name__)

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

# Загрузка всех регионов при старте приложения
AREAS_LIST = load_areas_from_file('utils/areas_cache.json')

@app.route('/')
def index():
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
        return render_template('index.html', areas=AREAS_LIST, resume_limit=None)

    # Используем первый токен
    access_token = access_tokens[0]
    employer_id = "104309"  # Номер компании из задания

    try:
        manager_id = get_manager_id(access_token)
        if not manager_id:
            return render_template('index.html', areas=AREAS_LIST, resume_limit=None)

        limits = get_resume_limits(employer_id, manager_id, access_token)
        resume_left = limits.get("left", {}).get("resume_view", 0)
    except Exception as e:
        print(f"[ERROR] Не удалось получить лимиты: {e}")
        resume_left = None

    return render_template('index.html', areas=AREAS_LIST, resume_limit=resume_left)

@app.route('/api/resume-limit')
def resume_limit_api():
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
        return jsonify({"limit": None})

    access_token = access_tokens[0]
    employer_id = "104309"

    try:
        manager_id = get_manager_id(access_token)
        if not manager_id:
            return jsonify({"limit": None})

        limits = get_resume_limits(employer_id, manager_id, access_token)
        return jsonify({"limit": limits.get("left", {}).get("resume_view_from_api", None)})
    except Exception as e:
        print(f"[ERROR] Ошибка получения лимита: {e}")
        return jsonify({"limit": None})

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

    from hh.api import get_company_vacancies, get_employer_id
    try:
        employer_id = get_employer_id(access_tokens[0])
        if not employer_id:
            return render_template('vacancies.html', error="Не удалось получить ID работодателя.", vacancies=[])

        vacancies_list = get_company_vacancies(access_tokens[0], employer_id)
        if not vacancies_list:
            return render_template('vacancies.html', error="Нет активных вакансий.", vacancies=[])

        result = []
        for vacancy in vacancies_list:
            vacancy_id = vacancy["id"]
            url = f"https://api.hh.ru/negotiations?vacancy_id={vacancy_id}"
            headers = {
                'Authorization': f'Bearer {access_tokens[0]}',
                'User-Agent': 'HH-User-Agent'
            }
            try:
                resp = requests.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                total = sum(coll["counters"]["total"] for coll in data.get("collections", []))
                unread = sum(coll["counters"]["with_updates"] for coll in data.get("collections", []))
                result.append({
                    "vacancy": vacancy,
                    "total_responses": total,
                    "new_responses": unread
                })
            except Exception as e:
                print(f"[ERROR] Ошибка при получении откликов для вакансии {vacancy_id}: {e}")

        return render_template('vacancies.html', vacancies=result, error=None)

    except Exception as e:
        print(f"[ERROR] Ошибка при получении данных: {e}")
        return render_template('vacancies.html', error="Ошибка получения вакансий. Проверьте права доступа или токен.", vacancies=[])


@app.route('/vacancy/<vacancy_id>/export')
def export_vacancy_resumes(vacancy_id):
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

    # Получаем все отклики по вакансии 
    from hh.api import findResumes
    def background_task(vacancy_id):
        nonlocal access_tokens
        result = None
        for idx, token in enumerate(access_tokens):
            print(f"[INFO] Используется токен #{idx + 1}")
            try:
                def update_progress(delta: int = 1):
                    with progress_lock:
                        if global_progress["step"] == "hh":
                            global_progress["current_hh"] += delta
                            if global_progress["current_hh"] >= global_progress["total_hh"]:
                                global_progress["step"] = "ai"

                # Здесь можно указать лимит, например, 100
                result = findResumes(
                    f"vacancy_id:{vacancy_id}",
                    access_token=token,
                    limit=100,
                    area_id="1",
                    progress_callback=update_progress
                )
                if result and result.get("items"):
                    print(f"[SUCCESS] Резюме загружены для вакансии {vacancy_id}")
                    break
            except Exception as e:
                print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
                continue
        else:
            with progress_lock:
                global_progress["status"] = "ошибка"
            return

        filename = f"resumes_output_{vacancy_id}.xlsx"
        from utils.excel_writer import append_resumes_to_excel
        description_input = ""  # Можно передать описание из БД или формы
        DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
        append_resumes_to_excel(result, filename=filename, description_input=description_input, deepseek_api_key=DEEPSEEK_API_KEY)

        with progress_lock:
            global_progress["status"] = "готово"
            global_progress["filename"] = filename

    thread = Thread(target=background_task, args=(vacancy_id,))
    thread.start()

    return render_template("progress.html")

@app.route('/vacancy/<vacancy_id>/export_new')
def export_new_responses(vacancy_id):
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

@app.route('/export', methods=['POST'])
def export_resumes():
    global global_progress

    keywords = request.form.get('keywords')
    area_id = request.form.get('area')
    count = request.form.get('count', '10')
    salary_to = request.form.get('salary_to')
    description_input = request.form.get('description_input', '')  # Описание вакансии

    if not keywords:
        return "Не указаны ключевые слова", 400

    try:
        count = int(count)
        if count <= 0 or count > 2000:
            return "Количество должно быть от 1 до 2000", 400
    except ValueError:
        return "Неверное значение количества", 400

    queries = [kw.strip() for kw in keywords.split(",")]
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
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
        return "Нет доступных ACCESS_TOKEN в .env", 500

    # === Установим общее число запросов к HeadHunter ===
    total_hh_requests = count + 1  # поиск + детализация

    with progress_lock:
        global_progress.update({
            "step": "hh",
            "total_hh": total_hh_requests,
            "current_hh": 0,
            "total_ai": count,
            "current_ai": 0,
            "status": "в процессе",
            "filename": None
        })

    def background_task():
        nonlocal queries, count, description_input, DEEPSEEK_API_KEY
        result = None
        for idx, token in enumerate(access_tokens):
            print(f"[INFO] Используется токен #{idx + 1}")
            try:
                def update_progress(delta: int = 1):
                    with progress_lock:
                        if global_progress["step"] == "hh":
                            global_progress["current_hh"] += delta
                            if global_progress["current_hh"] >= global_progress["total_hh"]:
                                global_progress["step"] = "ai"

                result = findResumes(*queries, access_token=token, limit=count, area_id=area_id, salary_to=salary_to, progress_callback=update_progress)
                if result and result.get("items"):
                    print(f"[SUCCESS] Резюме загружены с токеном #{idx + 1}")
                    break
            except Exception as e:
                print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
                continue
        else:
            with progress_lock:
                global_progress["status"] = "ошибка"
            return

        # === Переключаемся на AI-оценку ===
        filename = "resumes_output.xlsx"

        append_resumes_to_excel(result, filename=filename, description_input=description_input, deepseek_api_key=DEEPSEEK_API_KEY)

        with progress_lock:
            global_progress["status"] = "готово"
            global_progress["filename"] = filename

    thread = Thread(target=background_task)
    thread.start()

    return render_template("progress.html")


@app.route('/progress')
def get_progress():
    with progress_lock:
        current = global_progress["current_hh"] if global_progress["step"] == "hh" else global_progress["current_ai"]
        total = global_progress["total_hh"] if global_progress["step"] == "hh" else global_progress["total_ai"]
        step = global_progress["step"]
        status = global_progress["status"]
        percent = round((current / total) * 100) if total else 0

    return jsonify({
        "step": step,
        "percent": percent,
        "status": status,
        "filename": global_progress["filename"]
    })


@app.route('/download')
def download_file():
    filename = global_progress.get("filename")
    if filename and os.path.exists(filename):
        return send_file(filename, as_attachment=True)
    else:
        return "Файл не найден", 404


if __name__ == '__main__':
    app.run(debug=False)