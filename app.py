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
    count = request.form.get('count', '50')
    description_input = request.form.get('description_input', '')  # Новое поле

    print("[DEBUG] description_input:", description_input)

    if not keywords:
        return "Не указаны ключевые слова", 400

    try:
        count = int(count)
        if count <= 0 or count > 2000:
            return "Количество должно быть от 1 до 2000", 400
    except ValueError:
        return "Неверное значение количества", 400

    area_id = area_name_to_id(area_name)
    queries = [kw.strip() for kw in keywords.split(",")]
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

    # === Получаем список доступных токенов ===
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

    print(f"[INFO] Найдено {len(access_tokens)} токенов для использования.")

    # === Попробуем использовать токены по очереди ===
    result = None
    for idx, ACCESS_TOKEN in enumerate(access_tokens):
        print(f"[INFO] Используется токен #{idx + 1}")
        try:
            result = findResumes(*queries, access_token=ACCESS_TOKEN, limit=count)
            if result and result.get("items"):
                print(f"[SUCCESS] Резюме успешно загружены с токеном #{idx + 1}")
                break
        except Exception as e:
            print(f"[ERROR] Ошибка при использовании токена #{idx + 1}: {e}")
            continue
    else:
        return "[ERROR] Не удалось загрузить резюме ни с одним из токенов.", 500

    filename = "resumes_output.xlsx"
    append_resumes_to_excel(
        result,
        filename=filename,
        description_input=description_input,
        deepseek_api_key=DEEPSEEK_API_KEY
    )

    return send_file(filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=False)