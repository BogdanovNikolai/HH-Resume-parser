"""
data_manager/search_engine.py

Модуль содержит класс SearchEngine — утилиту для поиска резюме через HeadHunter API,
в том числе по ключевым словам или по ID вакансии (для получения откликов).
"""

from typing import List, Dict, Any, Optional
from config import log
from hh.api import findResumes, get_vacancy_negotiations
from utils.ai_evaluator import evaluate_candidate_match


class SearchEngine:
    """
    Класс для поиска резюме в HeadHunter API.

    Методы:
    - search_by_keywords() — поиск по ключевым словам.
    - search_by_vacancy() — получение откликов по ID вакансии.
    """

    def __init__(self):
        log.info("SearchEngine успешно инициализирован.")

    def search_by_keywords(
        self,
        keywords: str,
        area_id: Optional[str] = None,
        count: int = 10,
        salary_to: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Выполняет поиск резюме по ключевым словам.

        :param keywords: Строка с ключевыми словами.
        :param area_id: ID региона для фильтрации.
        :param count: Количество резюме для загрузки.
        :param salary_to: Верхняя граница зарплаты.
        :return: Список raw-резюме из HH API.
        """
        try:
            log.info(f"[SEARCH] Поиск по ключевым словам: {keywords}, регион: {area_id or 'все'}, кол-во: {count}")
            
            # Разбиваем ключевые слова на список
            queries = [kw.strip() for kw in keywords.split(",") if kw.strip()]
            if not queries:
                raise ValueError("Не указаны ключевые слова для поиска")

            # Вызываем API
            result = findResumes(*queries, limit=count, area_id=area_id, salary_to=salary_to)

            resumes = result.get("items", [])
            log.info(f"[SEARCH] Найдено {len(resumes)} резюме по запросу '{keywords}'")
            return resumes

        except Exception as e:
            log.error(f"[SEARCH] Ошибка при поиске по ключевым словам: {e}", exc_info=True)
            raise

    def search_by_vacancy(
        self,
        vacancy_id: str
    ) -> List[Dict[str, Any]]:
        """
        Получает список откликов на конкретную вакансию.

        :param vacancy_id: ID вакансии.
        :return: Список raw-резюме из HH API.
        """
        try:
            log.info(f"[SEARCH] Получение откликов по вакансии ID: {vacancy_id}")

            # Вызываем API
            result = get_vacancy_negotiations(vacancy_id)

            resumes = result.get("items", [])
            log.info(f"[SEARCH] Получено {len(resumes)} откликов по вакансии '{vacancy_id}'")
            return resumes

        except Exception as e:
            log.error(f"[SEARCH] Ошибка при получении откликов по вакансии '{vacancy_id}': {e}", exc_info=True)
            raise