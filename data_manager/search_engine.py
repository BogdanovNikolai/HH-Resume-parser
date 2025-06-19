from typing import Optional, Dict, Any, List
from hh.api import findResumes, get_new_responses, get_company_vacancies, get_vacancy_negotiations
from hh.api import get_manager_id, get_resume_limit
from config import app_config, log
from utils.token_executor import execute_with_token


class SearchEngine:
    def __init__(self):
        log.info("SearchEngine: Инициализация объекта SearchEngine")

    def find_resumes(self, query: str, area_ids: List[str], limit: int, salary_to: Optional[int]) -> Dict[str, Any]:
        log.info(f"SearchEngine: Поиск резюме по запросу '{query}', регионы: {area_ids}, лимит: {limit}, зарплата до: {salary_to}")
        try:
            result = execute_with_token(self._find_resumes_with_token, query, area_ids, limit, salary_to)
            if not result:
                log.error("SearchEngine: Не удалось найти резюме ни с одним из токенов")
                raise RuntimeError("Не найдено подходящих токенов для выполнения запроса")
            log.debug(f"SearchEngine: Получен результат поиска резюме (количество: {len(result.get('items', []))})")
            return result
        except Exception as e:
            log.error(f"SearchEngine: Ошибка при поиске резюме: {e}", exc_info=True)
            raise

    def get_new_responses(self, vacancy_id: str) -> Optional[Dict]:
        log.info(f"SearchEngine: Получение новых откликов для вакансии {vacancy_id}")
        try:
            response = get_new_responses(vacancy_id)
            if response:
                log.debug(f"SearchEngine: Получены новые отклики для вакансии {vacancy_id}")
            else:
                log.warning(f"SearchEngine: Нет новых откликов для вакансии {vacancy_id}")
            return response
        except Exception as e:
            log.error(f"SearchEngine: Ошибка при получении откликов для вакансии {vacancy_id}: {e}", exc_info=True)
            raise

    def get_company_vacancies(self) -> Optional[List[Dict]]:
        log.info("SearchEngine: Запрос списка вакансий компании")
        try:
            vacancies = get_company_vacancies()
            count = len(vacancies) if vacancies else 0
            log.debug(f"SearchEngine: Получено {count} вакансий компании")
            return vacancies
        except Exception as e:
            log.error("SearchEngine: Ошибка при получении вакансий компании", exc_info=True)
            raise

    def get_resume_limit(self) -> Optional[int]:
        log.info("SearchEngine: Запрос оставшегося лимита на просмотр резюме")
        try:
            result = execute_with_token(self._fetch_limit)
            if result is not None:
                log.info(f"SearchEngine: Остаток просмотров резюме: {result}")
            else:
                log.warning("SearchEngine: Не удалось получить лимит просмотров резюме")
            return result
        except Exception as e:
            log.error("SearchEngine: Ошибка при получении лимита на просмотр резюме", exc_info=True)
            raise

    def _fetch_limit(self, token: str) -> Optional[int]:
        log.debug("SearchEngine: Выполняется внутренний запрос лимита на просмотр резюме")
        employer_id = app_config.DEFAULT_EMPLOYER_ID
        log.info(f"SearchEngine: Получение ID менеджера для работодателя {employer_id}")
        manager_id = get_manager_id(token)
        if not manager_id:
            log.warning("SearchEngine: Не найден ID менеджера")
            return None
        log.info(f"SearchEngine: Запрос лимита просмотров резюме для менеджера {manager_id}")
        result = get_resume_limit(employer_id, manager_id, token)
        limit = result.get("left", {}).get("resume_view")
        log.debug(f"SearchEngine: Полученный лимит просмотров резюме: {limit}")
        return limit
    
    def _find_resumes_with_token(self, token: str, query: str, area_ids: List[str], limit: int, salary_to: Optional[int]) -> Dict[str, Any]:
        log.debug(f"SearchEngine: Поиск резюме с токеном {token[:10]}...")
        return findResumes(
            query,
            area_id=area_ids,
            limit=limit,
            salary_to=salary_to,
            access_token=token  # <-- здесь передаём токен
        )