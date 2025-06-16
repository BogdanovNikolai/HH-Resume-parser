from flask import Flask, render_template, request, send_file, jsonify
from hh.api import findResumes
from utils.excel_writer import append_resumes_to_excel
import os
from typing import List, Dict, Any, Optional
from threading import Thread, Lock
from progress import progress_lock, global_progress
import json

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
    return render_template('index.html', areas=AREAS_LIST)

@app.route('/export', methods=['POST'])
def export_resumes():
    global global_progress

    keywords = request.form.get('keywords')
    area_name = request.form.get('area', 'Россия')
    count = request.form.get('count', '50')
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

                result = findResumes(*queries, access_token=token, limit=count, progress_callback=update_progress)
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
        from utils.excel_writer import append_resumes_to_excel

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