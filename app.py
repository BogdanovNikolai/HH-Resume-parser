from flask import Flask, render_template, request, send_file
from hh.api import findResumes
from utils.excel_writer import append_resumes_to_excel
import os
from typing import List, Dict, Any, Optional

app = Flask(__name__)

# === Вспомогательные функции ===

def area_name_to_id(area_name: str) -> Optional[str]:
    """
    Простой маппинг названия региона в ID.
    Можно расширить или подключить к API HH /areas
    """
    areas = {
        "москва": "1",
        "санкт-петербург": "2",
        "екатеринбург": "3",
        "новосибирск": "4",
        "казань": "5",
        "челябинск": "6",
        "россия": "113"
    }
    return areas.get(area_name.lower().strip(), "113")  # По умолчанию — вся Россия


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/export', methods=['POST'])
def export_resumes():
    keywords = request.form.get('keywords')
    area_name = request.form.get('area', 'Россия')
    min_salary = request.form.get('min_salary')

    if not keywords:
        return "Не указаны ключевые слова", 400

    area_id = area_name_to_id(area_name)
    queries = [kw.strip() for kw in keywords.split(",")]

    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    if not ACCESS_TOKEN:
        return "ACCESS_TOKEN не найден в .env", 500

    try:
        result = findResumes(*queries, access_token=ACCESS_TOKEN, debug=False)
        filename = "resumes_output.xlsx"
        append_resumes_to_excel(result, filename=filename)

        return send_file(filename, as_attachment=True)
    except Exception as e:
        return f"[ERROR] {e}", 500


if __name__ == '__main__':
    app.run(debug=True)