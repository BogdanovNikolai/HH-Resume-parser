"""
Модуль `api` содержит реализацию клиентского API для работы с HeadHunter.

Основные возможности:
- авторизация через OAuth,
- автоматическое переключение аккаунтов при достижении лимитов,
- получение данных о вакансиях, откликах и резюме,
- поддержка пагинации и обработки ошибок.

Functions:
    auto_refresh_or_switch_account: декоратор для автоматического обновления токена или переключения аккаунта.
    get_me: получает данные текущего пользователя.
    get_employer_id: извлекает ID работодателя.
    get_manager_id: извлекает ID менеджера.
    get_company_vacancies: получает список вакансий компании.
    get_vacancy_negotiations: получает количество откликов по вакансии.
    get_new_responses: получает новые отклики по вакансии.
    get_resume_limit: получает лимиты на загрузку резюме.
    get_full_resume: загружает полные данные о резюме.
    findResumes: выполняет поиск резюме по ключевым словам.
"""

from typing import List, Dict, Any, Optional, Callable
import requests
import time
import random

# === Внешние зависимости ===
from config import app_config, log  # Импортируем единый логгер

# === Базовые параметры ===
BASE_URL = "https://api.hh.ru" 
USER_AGENT = "HH-User-Agent"

log.info("Модуль hh.api загружен. Начинаю работу с API HeadHunter.")


# === Декоратор для автоматического переключения аккаунтов и обновления токенов ===
def auto_refresh_or_switch_account(func):
    """
    Декоратор для автоматической обработки ошибок доступа и переключения аккаунтов.

    Если запрос завершается ошибкой 401/403 (токен истёк) или 429 (лимит исчерпан),
    декоратор либо обновляет токен, либо переключается на следующий аккаунт.

    Args:
        func (Callable): оборачиваемая функция.

    Returns:
        Callable: новая версия функции с обработкой ошибок.
    """

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
                log.warning(
                    f"[auto_refresh_or_switch_account] Ошибка HTTP: {status_code}, попытка {attempt} из {max_retries}")
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
    """
    Запрашивает данные текущего пользователя из HH API.

    Args:
        access_token (str): токен доступа к API.

    Returns:
        Dict[str, Any]: JSON-ответ с данными пользователя.
    """
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
    """
    Извлекает ID работодателя из данных текущего пользователя.

    Args:
        access_token (str): токен доступа к API.

    Returns:
        Optional[str]: ID работодателя или None.
    """
    log.debug("[get_employer_id] Получаю ID работодателя")
    data = get_me(access_token)
    eid = data.get("employer", {}).get("id")
    log.info(f"[get_employer_id] ID работодателя: {eid}")
    return eid


def get_manager_id(access_token: str) -> Optional[str]:
    """
    Извлекает ID менеджера из данных текущего пользователя.

    Args:
        access_token (str): токен доступа к API.

    Returns:
        Optional[str]: ID менеджера или None.
    """
    log.debug("[get_manager_id] Получаю ID менеджера")
    data = get_me(access_token)
    mid = data.get("manager", {}).get("id")
    log.info(f"[get_manager_id] ID менеджера: {mid}")
    return mid


# === Вакансии и отклики ===
@auto_refresh_or_switch_account
def get_company_vacancies(access_token: str, employer_id: str) -> List[Dict]:
    """
    Получает список вакансий для указанного работодателя.

    Args:
        access_token (str): токен доступа к API.
        employer_id (str): ID работодателя.

    Returns:
        List[Dict]: список вакансий.
    """
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
    """
    Получает количество откликов по указанной вакансии.

    Args:
        access_token (str): токен доступа к API.
        vacancy_id (str): ID вакансии.

    Returns:
        Dict[str, int]: словарь с количеством откликов и непрочитанных.
    """
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
    """
    Получает новые отклики по указанной вакансии.

    Args:
        vacancy_id (str): ID вакансии.
        access_token (str): токен доступа к API.

    Returns:
        Dict[str, Any]: словарь с найденными откликами.
    """
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
    """
    Получает лимиты на загрузку резюме для указанного работодателя и менеджера.

    Args:
        employer_id (str): ID работодателя.
        manager_id (str): ID менеджера.
        access_token (str): токен доступа к API.

    Returns:
        Dict[str, Any]: информация о лимите резюме.
    """
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


def get_full_resume(resume_id: str, access_token: str, account_num: int = 1,
                    progress_callback: Optional[Callable] = None) -> Optional[Dict]:
    """
    Загружает полные данные о резюме по его ID.

    Args:
        resume_id (str): ID резюме.
        access_token (str): токен доступа к API.
        account_num (int): номер аккаунта (для логирования).
        progress_callback (Optional[Callable]): callback-функция для обновления прогресса.

    Returns:
        Optional[Dict]: полные данные о резюме или None.
    """
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
    """
    Выполняет поиск резюме по указанным ключевым словам и фильтрам.

    Args:
        *queries (str): строки поиска.
        access_token (str): токен доступа к API.
        account_num (int): номер аккаунта (для логирования).
        limit (int): максимальное количество резюме для возврата.
        area_id (List[str]): список ID регионов.
        salary_to (Optional[int]): максимальная зарплата.
        progress_callback (Optional[Callable]): callback-функция для обновления прогресса.

    Returns:
        Dict[str, Any]: результаты поиска с метаданными.
    """
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
    """
    Загружает все страницы данных по указанному URL.

    Args:
        url (str): адрес API.
        headers (dict): заголовки запроса.
        params (dict): параметры запроса.

    Returns:
        List[Dict]: объединённый список элементов со всех страниц.
    """
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
    """
    Обновляет токен доступа для указанного аккаунта.

    Args:
        account_num (int): номер аккаунта.

    Returns:
        str: новый токен доступа.
    """
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
    """
    Переключается на следующий доступный аккаунт.

    Args:
        current_account (int): текущий номер аккаунта.

    Returns:
        Dict[str, Any]: новые учётные данные (токен и номер аккаунта).

    Raises:
        ConnectionError: если все аккаунты исчерпаны.
    """
    log.info(f"[switch_to_next_account] Переключаюсь на следующий аккаунт после #{current_account}")
    next_account = current_account + 1
    access_token = app_config.access_tokens[next_account - 1]
    if not access_token:
        log.error("[switch_to_next_account] Все аккаунты исчерпаны")
        raise ConnectionError("Все аккаунты исчерпаны.")
    log.info(f"[switch_to_next_account] Успешно переключились на аккаунт #{next_account}")
    return {"access_token": access_token, "account_num": next_account}