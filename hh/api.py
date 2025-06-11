import os
import time
import requests
import truststore
import json
import pandas
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI=os.environ.get("REDIRECT_URI")
CLIENT_ID=os.environ.get("CLIENT_ID")
CLIENT_SECRET=os.environ.get("CLIENT_SECRET")
APP_TOKEN=os.environ.get("APP_TOKEN")
CODE=os.environ.get("CODE")
ACCESS_TOKEN=os.environ.get("ACCESS_TOKEN")

def get_oauth_authorize_url(client_id: str, redirect_uri: str, state: str = "random_state") -> str:
    """
    Возвращает URL для открытия в браузере для авторизации пользователя.
    """
    base_url = "https://hh.ru/oauth/authorize" 
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "state": state
    }
    return f"{base_url}?{urlencode(params)}"

def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """
    Обменивает code на access_token.
    """
    token_url = "https://hh.ru/oauth/token" 
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    return response.json()

# url = get_oauth_authorize_url(CLIENT_ID, REDIRECT_URI)
# print("Перейдите по ссылке и скопируйте 'code':")
# print(url)

# token_data = exchange_code_for_token(CODE, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
# ACCESS_TOKEN = token_data["access_token"]
# print("Получен access_token:", ACCESS_TOKEN)

# [
#     {
#         "name": "Иван Иванов",
#         "url": "https://hh.ru/resume/...", 
#         "salary_expectation": "100 000 руб.",
#         "experience_years": 3,
#         "positions": ["Python разработчик", "Backend инженер"],
#         "skills": ["Django", "Flask", "PostgreSQL", "Git"],
#         "education": [
#             {
#                 "university": "МГУ",
#                 "specialization": "Программная инженерия",
#                 "year_graduated": 2020
#             }
#         ],
#         "location": "Москва",
#         "gender": "Мужской",
#         "age": 28,
#         "employment_type": "Полный день",
#         "schedule": "Полный рабочий день"
#     },
#     ...
# ]

# === Функция для поиска резюме на HH с поддержкой сложных запросов и полного парсинга ===

def findResumes(*queries, debug: bool = False) -> Dict[str, Any]:
    """
    Функция для поиска резюме на hh.ru с поддержкой простого и сложного поиска.

    Аргументы:
        *queries (str or tuple): 
            - str — простое ключевое слово (будет распарсено как: text, everywhere, any, all_time)
            - tuple — (text, field, logic, period), как в документации API
        debug (bool): если True, будет запрошено только первые 5 резюме

    Возвращает:
        dict: структурированный JSON-ответ от API HH с результатами поиска
    """

    base_url = 'https://api.hh.ru/resumes' 
    headers = {
        'Authorization': f'Bearer {ACCESS_TOKEN}',
        'User-Agent': 'HH-User-Agent',
        }
    params = {}

    # Проверяем типы входных данных и формируем параметры
    for i, query in enumerate(queries):
        if isinstance(query, str):
            # Простой режим: строка → автоматически преобразуется в дефолтный поиск
            param_prefix = f'text[{i}]' if i > 0 else 'text'
            params[param_prefix] = query
            params[f'{param_prefix}.field'] = 'everywhere'
            params[f'{param_prefix}.logic'] = 'any'
            params[f'{param_prefix}.period'] = 'all_time'

        elif isinstance(query, (tuple, list)) and len(query) == 4:
            # Расширенный режим: кортеж из 4 элементов
            text, field, logic, period = query

            valid_fields = {"everywhere", "experience", "skills", "education", "position"}
            valid_logic = {"all", "any"}
            valid_period = {"all_time", "last_year", "last_three_years"}

            if field not in valid_fields:
                raise ValueError(f"Недопустимое значение поля: {field}. Допустимые: {valid_fields}")
            if logic not in valid_logic:
                raise ValueError(f"Недопустимое значение логики: {logic}. Допустимые: {valid_logic}")
            if period not in valid_period:
                raise ValueError(f"Недопустимое значение периода: {period}. Допустимые: {valid_period}")

            param_prefix = f'text[{i}]' if i > 0 else 'text'
            params[param_prefix] = text
            params[f'{param_prefix}.field'] = field
            params[f'{param_prefix}.logic'] = logic
            params[f'{param_prefix}.period'] = period

        else:
            raise ValueError(
                f"Каждый аргумент должен быть строкой или кортежем из 4 элементов. "
                f"Получено: {query}"
            )

    # Стандартные параметры
    params['area'] = 113        # Россия
    params['per_page'] = 100    # Максимум на странице
    if debug:
        params['per_page'] = 5

    # Сборка всех страниц
    all_items = []
    page = 0

    while True:
        try:
            params['page'] = page
            response = requests.get(base_url, params=params, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ошибка при выполнении запроса к API: {e}")

        data = response.json()

        items = data.get('items', [])
        if not items:
            break

        all_items.extend(items)
        print(f"[INFO] Обработана страница {page}, собрано резюме: {len(all_items)}")

        if debug or page >= 1:
            break

        if page >= 199 and not debug:
            print("[WARNING] Достигнут лимит глубины выдачи (2000 записей). Остановка.")
            break

        page += 1

    # Формируем итоговый JSON
    json_result = {
        "query": params,
        "found": data.get("found"),
        "pages": data.get("pages"),
        "current_page": page,
        "items": all_items
    }

    return json_result



# # Поиск простой: Python разработчик
# result = findResumes("Python", "разработчик", debug=True)
# print(result)

# # Поиск сложной фразы: Java или Kotlin в опыте работы
# result = findResumes(
#     ("Java", "experience", "all", "last_year"),
#     ("Kotlin", "experience", "all", "last_year"),
#     debug=True
# )
# print(result)

# # Поиск: менеджер проекта в опыте или навыках за последние 3 года
# result = findResumes(
#     ("менеджер проекта", "experience", "all", "last_three_years"),
#     ("менеджер проекта", "skills", "all", "last_three_years"),
#     debug=True
# )
# print(result)