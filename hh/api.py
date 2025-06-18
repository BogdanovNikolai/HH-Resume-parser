import os
from typing import List, Dict, Any, Optional, Union, Callable, TypeVar
from functools import wraps
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv
import time
import random
from flask import current_app
from threading import Lock

load_dotenv()
progress_lock = Lock()
global_progress = {
    "total": 0,
    "current": 0,
    "status": "ожидание",
    "filename": None
}

# === REQUEST LOGGER DECORATOR ===
request_counter = 0

def log_request(method: str):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            global request_counter
            request_counter += 1
            url = args[0] if len(args) > 0 else kwargs.get('url', 'unknown')
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
def refresh_access_token(account_num: int) -> dict:
    """
    Обновляет access_token для заданного аккаунта.
    """
    prefix = f"{account_num}"
    token_url = "https://hh.ru/oauth/token" 
    data = {
        "grant_type": "refresh_token",
        "refresh_token": os.getenv(f"REFRESH_TOKEN{prefix}"),
        "client_id": os.getenv(f"CLIENT_ID{prefix}"),
        "client_secret": os.getenv(f"CLIENT_SECRET{prefix}"),
        "redirect_uri": os.getenv(f"REDIRECT_URI{prefix}")
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    new_tokens = response.json()

    with open('.env', 'r') as file:
        env_lines = {line.split('=')[0]: line.split('=')[1].strip('\n') for line in file.readlines() if '=' in line}

    env_lines[f'ACCESS_TOKEN{prefix}'] = new_tokens['access_token']
    if 'refresh_token' in new_tokens:
        env_lines[f'REFRESH_TOKEN{prefix}'] = new_tokens['refresh_token']

    with open('.env', 'w') as file:
        for key, value in env_lines.items():
            file.write(f"{key}={value}\n")

    print(f"[SUCCESS] Токен для аккаунта {account_num} обновлён.")
    return new_tokens


# === SWITCH TO NEXT ACCOUNT ===
def switch_to_next_account(current_account: int) -> Dict[str, Any]:
    next_account = current_account + 1
    print(f"ACCESS_TOKEN{next_account}")
    access_token = os.getenv(f"ACCESS_TOKEN{next_account}")
    if not access_token:
        raise ConnectionError("Все аккаунты исчерпаны. Лимит запросов исчерпан.")

    print(f"[INFO] Переключаемся на аккаунт {next_account}")
    return {"access_token": access_token, "account_num": next_account}


# === DECORATOR: автообновление токена или переход на другой аккаунт ===
F = TypeVar('F', bound=Callable[..., Any])
def auto_refresh_or_switch_account(func: F) -> F:
    @wraps(func)
    def wrapper(*args, **kwargs):
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                current_account = kwargs.get("account_num", 1)

                if status_code in (401, 403):
                    print(f"[INFO] Токен аккаунта {current_account} истёк. Обновляем...")
                    new_tokens = refresh_access_token(current_account)
                    kwargs["access_token"] = new_tokens["access_token"]
                    kwargs["account_num"] = current_account
                    continue

                elif status_code == 429:
                    print(f"[INFO] Лимит аккаунта {current_account} исчерпан. Переключаюсь на следующий.")
                    next_creds = switch_to_next_account(current_account)
                    kwargs["access_token"] = next_creds["access_token"]
                    kwargs["account_num"] = next_creds["account_num"]
                    continue

                else:
                    print(f"[ERROR] Неожиданная ошибка: {e}")
                    if attempt < max_retries:
                        print(f"[RETRY] Попытка {attempt}/{max_retries}")
                        time.sleep(3)
                    else:
                        raise

        return None
    return wrapper

def get_employer_id(access_token: str) -> Optional[str]:
    url = "https://api.hh.ru/me" 
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "HH-User-Agent"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("employer", {}).get("id")

def get_company_vacancies(access_token: str, employer_id: str) -> List[Dict[str, Any]]:
    url = "https://api.hh.ru/vacancies" 
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "HH-User-Agent"
    }
    params = {
        'employer_id': employer_id
    }

    all_vacancies = []
    page = 0

    while True:
        try:
            params['page'] = page
            response = requests.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if not items:
                print("[INFO] Больше нет данных.")
                break

            all_vacancies.extend(items)
            print(f"[INFO] Загружена страница вакансий #{page}, собрано: {len(all_vacancies)}")

            # Проверяем, достигли ли лимита в 200 страниц
            if page >= 199:
                print("[WARNING] Достигнут лимит в 200 страниц. Остановка.")
                break

            # Проверяем, есть ли ещё страницы по данным API
            if page >= data.get("pages", 0) - 1:
                print("[INFO] Все доступные страницы загружены.")
                break

            page += 1
            time.sleep(1)  # Защита от спама

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка при получении вакансий: {e}")
            if response.status_code == 403:
                print("[ACCESS_DENIED] Учетная запись не имеет прав на просмотр вакансий.")
            break

    return all_vacancies

def get_manager_id(access_token: str) -> Optional[str]:
    url = "https://api.hh.ru/me" 
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "HH-User-Agent"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data.get("manager", {}).get("id")


def get_resume_limits(employer_id: str, manager_id: str, access_token: str) -> dict:
    url = f"https://api.hh.ru/employers/{employer_id}/managers/{manager_id}/limits/resume" 
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "HH-User-Agent"
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

# === PARSE FULL RESUME ===
def get_full_resume(resume_id: str, access_token: str, account_num: int, max_retries: int = 5, base_delay: float = 2.0, progress_callback: Optional[Callable[[int], None]] = None) -> Optional[Dict[str, Any]]:
    url = f"https://api.hh.ru/resumes/{resume_id}" 
    headers = {
        'Authorization': f'Bearer {access_token}',
        'User-Agent': 'HH-User-Agent'
    }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            if progress_callback:
                progress_callback(1)
            return response.json()
        except requests.exceptions.RequestException as e:
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

def get_new_responses(vacancy_id: str, access_token: str) -> Dict[str, Any]:
    """
    Получает список новых откликов на вакансию.
    
    :param vacancy_id: ID вакансии
    :param access_token: Токен доступа HH.ru
    :return: JSON-ответ с резюме кандидатов
    """
    url = f"https://api.hh.ru/negotiations/response" 
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": "HH-User-Agent"
    }
    params = {
        "vacancy_id": vacancy_id,
        "show_only_new_responses": True
    }

    all_items = []
    page = 0
    while True:
        # Добавляем параметры пагинации
        current_params = params.copy()
        current_params.update({"page": page, "per_page": 20})  # максимум 100 записей на странице

        try:
            response = requests.get(url=url, headers=headers, params=current_params)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            all_items.extend(items)

            # Проверяем, есть ли ещё страницы
            if page >= data.get("pages", 0) - 1:
                break

            page += 1

        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка при получении новых откликов: {e}")
            break

    print(f"[SUCCESS] Загружено {len(all_items)} новых откликов")
    return {"items": all_items}

# === findResumes с поддержкой нескольких аккаунтов ===
@auto_refresh_or_switch_account
def findResumes(*queries, access_token: str, account_num: int = 1, debug: bool = False, per_page: int = 100, limit: int = 100, area_id: str = "113", salary_to: int = None, progress_callback: Optional[Callable[[int], None]] = None) -> Dict[str, Any]:
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

    params['area'] = area_id
    if salary_to:
        params['salary_to'] = salary_to
    # params['label'] = "only_with_salary"
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

        if progress_callback:
            progress_callback(1)  # Первый запрос — общий поиск

        full_resumes = []
        for item in items:
            full_data = get_full_resume(item['id'], access_token, account_num, progress_callback=progress_callback)
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