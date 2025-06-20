"""
Модуль `app` содержит основное Flask-приложение для поиска, обработки и экспорта резюме из HeadHunter.

Endpoints:
    - /vacancy/<vacancy_id>/start — запуск задачи по поиску резюме по вакансии.
    - /progress/<task_id> — получение прогресса фоновой задачи.
    - /download/<task_id> — скачивание результатов задачи.
    - /vacancy/<vacancy_id>/export_new — экспорт новых откликов по вакансии.
    - /export (POST) — запуск поиска резюме по ключевым словам.
    - /vacancies — список вакансий компании.
    - / — главная страница с формой поиска.
    - /api/resume-limit — получение лимита на загрузку резюме.

Functions:
    start_task: запуск задачи поиска резюме по ID вакансии.
    get_task_progress: получение текущего прогресса задачи.
    download_file: скачивание файла с результатами задачи.
    export_new_responses: экспорт новых откликов по вакансии.
    export_resumes: запуск фоновой задачи поиска резюме по ключевым словам.
    vacancies: отображение списка вакансий компании.
    index: главная страница приложения.
    get_limit: получение лимита на загрузку резюме.
"""

import os
from threading import Thread
from flask import Flask, render_template, request, send_file, jsonify
from data_manager import data_manager
import uuid

# === Инициализация Flask-приложения ===
app = Flask(__name__)


@app.route('/vacancy/<vacancy_id>/start')
def start_task(vacancy_id):
    """
    Запускает фоновую задачу поиска резюме по указанной вакансии.

    Args:
        vacancy_id (str): ID вакансии.

    Returns:
        JSON: {"task_id": str}.
    """
    task_id = str(uuid.uuid4())
    data_manager.start_search_task(task_id=task_id, vacancy_id=vacancy_id)
    return jsonify({"task_id": task_id})


@app.route('/progress/<task_id>')
def get_task_progress(task_id):
    """
    Возвращает текущий прогресс выполнения задачи.

    Args:
        task_id (str): уникальный идентификатор задачи.

    Returns:
        JSON: информация о шаге, проценте выполнения, статусе и имени файла.
    """
    progress_data = data_manager.get_task_progress(task_id)
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


@app.route('/download/<task_id>')
def download_file(task_id):
    """
    Скачивание файла с результатами задачи.

    Args:
        task_id (str): уникальный идентификатор задачи.

    Returns:
        File: отправляет файл пользователю или ошибку 404.
    """
    file_path = data_manager.export_task_results(task_id, format="excel")
    if file_path and os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return "Файл не найден", 404


@app.route('/vacancy/<vacancy_id>/export_new')
def export_new_responses(vacancy_id):
    """
    Экспортирует новые отклики по указанной вакансии в Excel.

    Args:
        vacancy_id (str): ID вакансии.

    Returns:
        File: отправляет Excel-файл с новыми откликами.
    """
    result = data_manager.get_new_responses(vacancy_id)
    if not result or not result.get("items"):
        return "Не удалось получить новые отклики", 500
    filename = f"new_resumes_output_{vacancy_id}.xlsx"
    data_manager.exporter.export_to_excel(result["items"], filename=filename)
    return send_file(f"output\\{filename}", as_attachment=True)


@app.route('/export', methods=['POST'])
def export_resumes():
    """
    Запускает фоновый поиск резюме по ключевым словам.

    Берёт данные из формы:
        - keywords: ключевые слова для поиска.
        - area: регион(ы).
        - count: количество резюме.
        - salary_to: максимальная зарплата.
        - description_input: описание вакансии для AI-анализа.

    Returns:
        Template: перенаправление на страницу прогресса.
    """
    keywords = request.form.get('keywords')
    area_ids = request.form.getlist('area')
    count = int(request.form.get('count', '10'))
    salary_to = request.form.get('salary_to')
    description_input = request.form.get('description_input')

    if not keywords:
        return "Не указаны ключевые слова", 400

    task_id = str(uuid.uuid4())
    Thread(
        target=data_manager.start_search_task,
        kwargs={
            "task_id": task_id,
            "keywords": keywords,
            "area_ids": area_ids,
            "limit": count,
            "description_input": description_input,
            "salary_to": salary_to
        }
    ).start()

    return render_template('progress.html', task_id=task_id)


@app.route('/vacancies')
def vacancies():
    """
    Отображает список вакансий компании.

    Returns:
        Template: vacancies.html с данными о вакансиях.
    """
    result = data_manager.get_company_vacancies()
    if not result:
        return "Не удалось загрузить вакансии", 500
    return render_template('vacancies.html', vacancies=result, error=None)


@app.route('/')
def index():
    """
    Главная страница приложения.

    Returns:
        Template: index.html с формой поиска резюме.
    """
    resume_limit = data_manager.get_resume_limit()
    return render_template('index.html', areas=data_manager.areas_list, resume_limit=resume_limit)


@app.route('/api/resume-limit')
def get_limit():
    """
    Возвращает текущий лимит на загрузку резюме.

    Returns:
        JSON: {"limit": int}.
    """
    resume_limit = data_manager.get_resume_limit()
    return jsonify({"limit": resume_limit})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)