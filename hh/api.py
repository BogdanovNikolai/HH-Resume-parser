from typing import List, Dict, Any, Optional, Callable
import requests
import time
import random
from config import app_config

# === Базовые параметры ===
BASE_URL = "https://api.hh.ru" 
USER_AGENT = "HH-User-Agent"

# === Автоматическое переключение аккаунтов и обновление токенов ===
def auto_refresh_or_switch_account(func):
    def wrapper(*args, **kwargs):
        max_retries = 3
        current_account = kwargs.get("account_num", 1)
        access_token = kwargs.get("access_token")

        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code

                if status_code in (401, 403):
                    print(f"[INFO] Токен аккаунта {current_account} истёк. Обновляем...")
                    new_token = refresh_access_token(current_account)
                    kwargs["access_token"] = new_token
                    continue
                elif status_code == 429:
                    print(f"[INFO] Лимит аккаунта {current_account} исчерпан. Переключаюсь на следующий.")
                    next_creds = switch_to_next_account(current_account)
                    kwargs["access_token"] = next_creds["access_token"]
                    kwargs["account_num"] = next_creds["account_num"]
                    continue
                else:
                    print(f"[ERROR] Неожиданная ошибка: {e}")
                    raise
        return None
    return wrapper


# === Получение данных текущего пользователя ===
def get_me(access_token: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_employer_id(access_token: str) -> Optional[str]:
    data = get_me(access_token)
    return data.get("employer", {}).get("id")


def get_manager_id(access_token: str) -> Optional[str]:
    data = get_me(access_token)
    return data.get("manager", {}).get("id")


# === Вакансии и отклики ===
def get_company_vacancies(access_token: str, employer_id: str) -> List[Dict]:
    url = f"{BASE_URL}/vacancies"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    params = {"employer_id": employer_id}
    return fetch_paginated_data(url, headers=headers, params=params)


def get_vacancy_negotiations(access_token: str, vacancy_id: str) -> Dict[str, int]:
    url = f"{BASE_URL}/negotiations"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    params = {"vacancy_id": vacancy_id}
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    total = sum(coll["counters"]["total"] for coll in data.get("collections", []))
    unread = sum(coll["counters"]["with_updates"] for coll in data.get("collections", []))
    return {"total": total, "unread": unread}


def get_new_responses(vacancy_id: str, access_token: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/negotiations/response"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "vacancy_id": vacancy_id,
        "show_only_new_responses": True
    }

    all_items = []
    page = 0
    while True:
        current_params = params.copy()
        current_params.update({"page": page, "per_page": 20})
        try:
            response = requests.get(url, headers=headers, params=current_params)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            all_items.extend(items)
            if page >= data.get("pages", 0) - 1:
                break
            page += 1
        except Exception as e:
            print(f"[ERROR] Ошибка при получении новых откликов: {e}")
            break
    return {"items": all_items}


# === Резюме ===
def get_resume_limits(employer_id: str, manager_id: str, access_token: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/employers/{employer_id}/managers/{manager_id}/limits/resume"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_full_resume(resume_id: str, access_token: str, account_num: int = 1, progress_callback: Optional[Callable] = None) -> Optional[Dict]:
    url = f"{BASE_URL}/resumes/{resume_id}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    for attempt in range(3):
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            if progress_callback:
                progress_callback(1)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Ошибка загрузки резюме {resume_id}: {e}")
            time.sleep(2)
    return None


@auto_refresh_or_switch_account
def findResumes(
    *queries,
    access_token: str,
    account_num: int = 1,
    limit: int = 100,
    area_id: List[str] = ["113"],
    salary_to: Optional[int] = None,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    url = f"{BASE_URL}/resumes"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }

    params = {}
    for i, query in enumerate(queries):
        if isinstance(query, str):
            param_name = f"text[{i}]" if i > 0 else "text"
            params[param_name] = query

    params["area"] = area_id
    params["relocation"] = "living"
    if salary_to:
        params["salary_to"] = salary_to
    params["per_page"] = min(limit, 100)

    all_items = []
    page = 0
    
    while len(all_items) < limit:
        try:
            params["page"] = page
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
        except Exception as e:
            raise ConnectionError(f"Ошибка при поиске резюме: {e}")

        data = response.json()
        items = data.get("items", [])

        if not items:
            break

        full_resumes = []
        for item in items:
            resume = get_full_resume(item["id"], access_token, progress_callback=progress_callback)
            if resume:
                full_resumes.append(resume)

        all_items.extend(full_resumes)
        if len(all_items) >= limit:
            break
        if page >= 199:
            print("[WARNING] Достигнут лимит глубины выдачи (200 страниц).")
            break
        page += 1

    return {
        "query": params,
        "found": data.get("found"),
        "pages": data.get("pages"),
        "items": all_items[:limit]
    }


# === Вспомогательные функции ===
def fetch_paginated_data(url: str, headers: dict, params: dict = None) -> List[Dict]:
    if params is None:
        params = {}
    all_items = []
    page = 0
    while True:
        try:
            params["page"] = page
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            all_items.extend(items)
            if page >= data.get("pages", 0) - 1:
                break
            page += 1
        except Exception as e:
            print(f"[ERROR] Ошибка при пагинации: {e}")
            break
    return all_items


def refresh_access_token(account_num: int) -> str:
    prefix = f"{account_num}"
    token_url = "https://hh.ru/oauth/token" 
    data = {
        "grant_type": "refresh_token",
        "refresh_token": app_config.refresh_tokens[prefix],
        "client_id": app_config.client_ids[prefix],
        "client_secret": app_config.client_secrets[prefix],
        "redirect_uri": app_config.redirect_uris[prefix]
    }
    response = requests.post(token_url, data=data)
    response.raise_for_status()
    tokens = response.json()
    return tokens["access_token"]


def switch_to_next_account(current_account: int) -> Dict[str, Any]:
    next_account = current_account + 1
    access_token = app_config.access_tokens[next_account - 1]
    if not access_token:
        raise ConnectionError("Все аккаунты исчерпаны.")
    print(f"[INFO] Переключаюсь на аккаунт #{next_account}")
    return {"access_token": access_token, "account_num": next_account}