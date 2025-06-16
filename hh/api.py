import os
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar
from functools import wraps
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
import time
import random

load_dotenv()

# === REQUEST LOGGER DECORATOR ===
request_counter = 0

def log_request(method: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            global request_counter
            request_counter += 1
            url = args[0] if len(args) > 0 else kwargs.get('url', 'unknown')
            # Убираем извлечение params, т.к. они уже в URL
            headers = kwargs.get('headers')

            print(f"\n[REQUEST #{request_counter}]")
            print(f"Method: {method}")
            print(f"URL: {url}")
            if headers:
                print(f"Headers: {headers}")

            return func(*args, **kwargs)
        return wrapper
    return decorator


# Переопределяем методы requests с декоратором
original_get = requests.get
original_post = requests.post

requests.get = log_request("GET")(original_get)
requests.post = log_request("POST")(original_post)


# === REFRESH TOKEN ===
def refresh_access_token(refresh_token: str, client_id: str, client_secret: str, redirect_uri: str) -> dict:
    """
    Обновляет access_token через refresh_token.
    """
    token_url = "https://hh.ru/oauth/token" 
    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    new_tokens = response.json()

    with open('.env', 'r') as file:
        env_lines = {line.split('=')[0]: line.split('=')[1].strip('\n') for line in file.readlines() if '=' in line}

    env_lines['ACCESS_TOKEN'] = new_tokens['access_token']
    if 'refresh_token' in new_tokens:
        env_lines['REFRESH_TOKEN'] = new_tokens['refresh_token']

    with open('.env', 'w') as file:
        for key, value in env_lines.items():
            file.write(f"{key}={value}\n")

    return new_tokens


# === DECORATOR: автообновление токена при 401/403 ===
F = TypeVar('F', bound=Callable[..., Any])
def auto_refresh_token(func: F) -> F:
    """
    Декоратор для автоматического обновления токена при получении ошибки 401 или 403.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 403):
                print("[INFO] Токен недействителен или истёк. Обновляем...")
                CLIENT_ID = os.getenv("CLIENT_ID")
                CLIENT_SECRET = os.getenv("CLIENT_SECRET")
                REDIRECT_URI = os.getenv("REDIRECT_URI")
                REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

                if not REFRESH_TOKEN:
                    raise ConnectionError("Нет refresh_token. Нужна новая авторизация.")

                new_tokens = refresh_access_token(REFRESH_TOKEN, CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
                print("[SUCCESS] Токен обновлён.")
                kwargs["access_token"] = new_tokens["access_token"]
                return func(*args, **kwargs)
            else:
                raise

    return wrapper


# === PARSE FULL RESUME ===
def get_full_resume(resume_id: str, access_token: str, max_retries: int = 5, base_delay: float = 2.0) -> Optional[Dict[str, Any]]:
    """
    Получает полные данные резюме по resume_id.
    При ошибке 429 — ждёт и пробует снова.
    Использует экспоненциальную задержку при повторах.
    """
    url = f"https://api.hh.ru/resumes/{resume_id}" 
    headers = {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': 'HH-User-Agent'
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as e:
            if response.status_code == 429:
                delay = base_delay * (2 ** attempt) + random.uniform(0.5, 1.5)
                print(f"[RATE LIMIT] Попытка {attempt}/{max_retries}. Ждём {delay:.2f} секунд...")
                time.sleep(delay)

            elif response.status_code in (403, 401):
                print("[ACCESS DENIED] Проверь права доступа или токен.")
                return None

            else:
                print(f"[ERROR] Ошибка {response.status_code} для {resume_id}: {e}")
                return None

    print(f"[FAILED] Не удалось загрузить резюме {resume_id} после {max_retries} попыток.")
    return None


# === findResumes с автообновлением токена ===
@auto_refresh_token
def findResumes(*queries, access_token: str, debug: bool = False, per_page: int = 100, limit: int = 100) -> Dict[str, Any]:
    """
    Функция для поиска резюме на hh.ru с поддержкой простого и сложного поиска.
    """
    base_url = 'https://api.hh.ru/resumes' 
    headers = {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': 'HH-User-Agent',
    }
    params = {}

    for i, query in enumerate(queries):
        if isinstance(query, str):
            param_prefix = f'text[{i}]' if i > 0 else 'text'
            params[param_prefix] = query
            #params[f'{param_prefix}.field'] = 'everywhere'
            #params[f'{param_prefix}.logic'] = 'any'
            #params[f'{param_prefix}.period'] = 'all_time'

        elif isinstance(query, (tuple, list)) and len(query) == 4:
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
            # params[f'{param_prefix}.field'] = field
            # params[f'{param_prefix}.logic'] = logic
            # params[f'{param_prefix}.period'] = period

        else:
            raise ValueError(
                f"Каждый аргумент должен быть строкой или кортежем из 4 элементов. "
                f"Получено: {query}"
            )

    params['area'] = 113  # Россия
    params['per_page'] = min(per_page, limit)

    all_items = []
    page = 0

    while len(all_items) < limit:
        try:
            params['page'] = page
            encoded_params = urlencode(params)
            full_url = f"{base_url}?{encoded_params}"
            response = requests.get(full_url, headers=headers)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"Ошибка при выполнении запроса к API: {e}")
        data = response.json()
        items = data.get('items', [])
        if not items:
            break
        full_resumes = []
        for item in items:
            full_data = get_full_resume(item['id'], access_token)
            if full_data:
                full_resumes.append(full_data)
        all_items.extend(full_resumes)
        print(f"[INFO] Обработана страница {page}, собрано резюме: {len(all_items)}")
        if len(all_items) >= limit:
            break
        if page >= 199 and not debug:
            print("[WARNING] Достигнут лимит глубины выдачи (2000 записей). Остановка.")
            break
        page += 1

    json_result = {
        "query": params,
        "found": data.get("found"),
        "pages": data.get("pages"),
        "current_page": page,
        "items": all_items
    }

    return json_result