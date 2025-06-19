from typing import List, Dict, Any, Optional, Callable
import requests
import time
import random
from config import app_config, log  # Импортируем единый логгер

# === Базовые параметры ===
BASE_URL = "https://api.hh.ru" 
USER_AGENT = "HH-User-Agent"

log.info("Модуль hh.api загружен. Начинаю работу с API HeadHunter.")


# === Автоматическое переключение аккаунтов и обновление токенов ===
def auto_refresh_or_switch_account(func):
    def wrapper(*args, **kwargs):
        max_retries = 3
        current_account = kwargs.get("account_num", 1)
        access_token = kwargs.get("access_token")

        log.info(f"[auto_refresh_or_switch_account] Вызов функции {func.__name__} с аккаунтом #{current_account}")
        for attempt in range(1, max_retries + 1):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.HTTPError as e:
                status_code = e.response.status_code
                log.warning(f"[auto_refresh_or_switch_account] Ошибка HTTP: {status_code}, попытка {attempt} из {max_retries}")

                if status_code in (401, 403):
                    log.info(f"Токен аккаунта #{current_account} истёк. Обновляем...")
                    new_token = refresh_access_token(current_account)
                    kwargs["access_token"] = new_token
                    continue
                elif status_code == 429:
                    log.info(f"Лимит аккаунта #{current_account} исчерпан. Переключаюсь на следующий.")
                    next_creds = switch_to_next_account(current_account)
                    kwargs["access_token"] = next_creds["access_token"]
                    kwargs["account_num"] = next_creds["account_num"]
                    continue
                else:
                    log.error(f"[auto_refresh_or_switch_account] Неожиданная ошибка: {e}", exc_info=True)
                    raise
        return None
    return wrapper


# === Получение данных текущего пользователя ===
def get_me(access_token: str) -> Dict[str, Any]:
    log.debug("[get_me] Запрашиваю данные текущего пользователя")
    url = f"{BASE_URL}/me"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        log.debug("[get_me] Данные пользователя успешно получены")
        return response.json()
    except Exception as e:
        log.error(f"[get_me] Ошибка получения данных пользователя: {e}", exc_info=True)
        raise


def get_employer_id(access_token: str) -> Optional[str]:
    log.debug("[get_employer_id] Получаю ID работодателя")
    data = get_me(access_token)
    eid = data.get("employer", {}).get("id")
    log.info(f"[get_employer_id] ID работодателя: {eid}")
    return eid


def get_manager_id(access_token: str) -> Optional[str]:
    log.debug("[get_manager_id] Получаю ID менеджера")
    data = get_me(access_token)
    mid = data.get("manager", {}).get("id")
    log.info(f"[get_manager_id] ID менеджера: {mid}")
    return mid


# === Вакансии и отклики ===
@auto_refresh_or_switch_account
def get_company_vacancies(access_token: str, employer_id: str) -> List[Dict]:
    log.info(f"[get_company_vacancies] Получаю список вакансий для работодателя {employer_id}")
    url = f"{BASE_URL}/vacancies"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    params = {"employer_id": employer_id}
    result = fetch_paginated_data(url, headers=headers, params=params)
    log.info(f"[get_company_vacancies] Получено {len(result)} вакансий")
    return result


@auto_refresh_or_switch_account
def get_vacancy_negotiations(access_token: str, vacancy_id: str) -> Dict[str, int]:
    log.info(f"[get_vacancy_negotiations] Получаю количество откликов по вакансии {vacancy_id}")
    url = f"{BASE_URL}/negotiations"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    params = {"vacancy_id": vacancy_id}
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        total = sum(coll["counters"]["total"] for coll in data.get("collections", []))
        unread = sum(coll["counters"]["with_updates"] for coll in data.get("collections", []))
        log.info(f"[get_vacancy_negotiations] Откликов: {total}, непрочитанных: {unread}")
        return {"total": total, "unread": unread}
    except Exception as e:
        log.error(f"[get_vacancy_negotiations] Ошибка получения откликов: {e}", exc_info=True)
        raise


@auto_refresh_or_switch_account
def get_new_responses(vacancy_id: str, access_token: str) -> Dict[str, Any]:
    log.info(f"[get_new_responses] Получаю новые отклики по вакансии {vacancy_id}")
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
            log.debug(f"[get_new_responses] Загрузка страницы {page}")
            response = requests.get(url, headers=headers, params=current_params)
            response.raise_for_status()
            data = response.json()
            items = data.get("items", [])
            all_items.extend(items)
            if page >= data.get("pages", 0) - 1:
                break
            page += 1
        except Exception as e:
            log.error(f"[get_new_responses] Ошибка при получении новых откликов: {e}", exc_info=True)
            break
    log.info(f"[get_new_responses] Найдено новых откликов: {len(all_items)}")
    return {"items": all_items}


# === Резюме ===
@auto_refresh_or_switch_account
def get_resume_limit(employer_id: str, manager_id: str, access_token: str) -> Dict[str, Any]:
    log.info(f"[get_resume_limit] Запрашиваю лимит резюме для работодателя {employer_id}, менеджера {manager_id}")
    url = f"{BASE_URL}/employers/{employer_id}/managers/{manager_id}/limits/resume"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": USER_AGENT
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        log.info(f"[get_resume_limit] Лимит резюме: {data.get('left', {})}")
        return data
    except Exception as e:
        log.error(f"[get_resume_limit] Ошибка получения лимита резюме: {e}", exc_info=True)
        raise


def get_full_resume(resume_id: str, access_token: str, account_num: int = 1, progress_callback: Optional[Callable] = None) -> Optional[Dict]:
    log.debug(f"[get_full_resume] Загрузка полного резюме {resume_id}")
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
            log.info(f"[get_full_resume] Резюме {resume_id} успешно загружено")
            return response.json()
        except requests.exceptions.RequestException as e:
            log.error(f"[get_full_resume] Ошибка загрузки резюме {resume_id}: {e}", exc_info=True)
            time.sleep(2)
    log.warning(f"[get_full_resume] Не удалось загрузить резюме {resume_id} после 3 попыток")
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
    log.info(f"[findResumes] Поиск резюме. Ключевые слова: {queries}, регион: {area_id}, лимит: {limit}")
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
            log.debug(f"[findResumes] Страница {page}")
            params["page"] = page
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
        except Exception as e:
            log.error(f"[findResumes] Ошибка при поиске резюме: {e}", exc_info=True)
            raise

        data = response.json()
        items = data.get("items", [])

        if not items:
            log.warning("[findResumes] Нет результатов на этой странице")
            break

        full_resumes = []
        for item in items:
            resume = get_full_resume(item["id"], access_token, progress_callback=progress_callback)
            if resume:
                full_resumes.append(resume)

        all_items.extend(full_resumes)
        if len(all_items) >= limit:
            log.info(f"[findResumes] Лимит ({limit}) достигнут")
            break
        if page >= 199:
            log.warning("[findResumes] Достигнут лимит глубины выдачи (200 страниц)")
            break
        page += 1

    log.info(f"[findResumes] Найдено резюме: {len(all_items)}")
    return {
        "query": params,
        "found": data.get("found"),
        "pages": data.get("pages"),
        "items": all_items[:limit]
    }


# === Вспомогательные функции ===
def fetch_paginated_data(url: str, headers: dict, params: dict = None) -> List[Dict]:
    log.debug(f"[fetch_paginated_data] Запрос пагинированных данных с {url}")
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
            log.error(f"[fetch_paginated_data] Ошибка при пагинации: {e}", exc_info=True)
            break
    log.info(f"[fetch_paginated_data] Получено {len(all_items)} записей")
    return all_items


def refresh_access_token(account_num: int) -> str:
    log.info(f"[refresh_access_token] Обновляю токен аккаунта #{account_num}")
    prefix = f"{account_num}"
    token_url = "https://hh.ru/oauth/token" 
    data = {
        "grant_type": "refresh_token",
        "refresh_token": app_config.refresh_tokens[prefix],
        "client_id": app_config.client_ids[prefix],
        "client_secret": app_config.client_secrets[prefix],
        "redirect_uri": app_config.redirect_uris[prefix]
    }
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        tokens = response.json()
        log.info(f"[refresh_access_token] Токен аккаунта #{account_num} обновлён")
        return tokens["access_token"]
    except Exception as e:
        log.error(f"[refresh_access_token] Ошибка обновления токена: {e}", exc_info=True)
        raise


def switch_to_next_account(current_account: int) -> Dict[str, Any]:
    log.info(f"[switch_to_next_account] Переключаюсь на следующий аккаунт после #{current_account}")
    next_account = current_account + 1
    access_token = app_config.access_tokens[next_account - 1]
    if not access_token:
        log.error("[switch_to_next_account] Все аккаунты исчерпаны")
        raise ConnectionError("Все аккаунты исчерпаны.")
    log.info(f"[switch_to_next_account] Успешно переключились на аккаунт #{next_account}")
    return {"access_token": access_token, "account_num": next_account}