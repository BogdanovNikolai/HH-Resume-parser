"""
Модуль `resume_processor` содержит класс ResumeProcessor — утилиту для обработки и форматирования
сырых данных о резюме, полученных из HeadHunter API.

Classes:
    ResumeProcessor: класс для преобразования и подготовки данных о резюме к дальнейшей обработке и хранению.

Functions:
    Нет функций верхнего уровня.
"""

from typing import Dict, Any, List, Optional
from config import log


class ResumeProcessor:
    """
    Класс для обработки и форматирования резюме из HeadHunter API.

    Предоставляет методы для преобразования raw JSON-ответов HH в структурированные данные,
    пригодные для отображения, анализа и сохранения в БД.

    Attributes:
        Нет публичных атрибутов. Используются внутренние методы и логирование.
    """

    def __init__(self):
        """Инициализирует экземпляр ResumeProcessor."""
        log.info("ResumeProcessor успешно инициализирован.")

    def to_db_format(self, formatted_resume: dict) -> dict:
        """
        Преобразует форматированное резюме в вид, подходящий для хранения в БД.

        Args:
            formatted_resume (dict): словарь с данными резюме после вызова format_resume().

        Returns:
            dict: данные в формате, готовом к записи в базу данных.
        """
        return {
            "resume_id": formatted_resume["ID Резюме"],
            "first_name": formatted_resume["Имя"],
            "last_name": formatted_resume["Фамилия"],
            "middle_name": formatted_resume["Отчество"],
            "gender": formatted_resume["Пол"],
            "age": formatted_resume["Возраст"],
            "salary": formatted_resume["Желаемая ЗП"],
            "title": formatted_resume["Должность"],
            "area": formatted_resume["Город"],
            "experience": formatted_resume["Опыт работы"],
            "skills": formatted_resume["Ключевые навыки"],
            "contacts": formatted_resume["Контакты"],
            "link": formatted_resume["Ссылка на резюме"],
            "updated_at": formatted_resume["Обновлено"],
            "total_experience": formatted_resume.get("Общий опыт (лет)"),
            "match_percent": formatted_resume.get("match_percent"),
            "explanation": formatted_resume.get("explanation")
        }

    def format_resume(self, resume_json: Dict[str, Any], description_input: Optional[str] = None) -> Dict[str, Any]:
        """
        Преобразует raw резюме из HH API в структурированный вид для отображения.

        Args:
            resume_json (Dict[str, Any]): сырые данные о резюме из HH API.
            description_input (Optional[str]): описание вакансии для AI-оценки (не используется напрямую здесь).

        Returns:
            Dict[str, Any]: словарь с ключами:
                - ID Резюме
                - Имя
                - Фамилия
                - Отчество
                - Пол
                - Возраст
                - Желаемая ЗП
                - Должность
                - Город
                - Опыт работы
                - Ключевые навыки
                - Контакты
                - Ссылка на резюме
                - Обновлено
                - Общий опыт (лет)
        """
        try:
            result = {
                "ID Резюме": resume_json.get("id", "Не указано"),
                "Имя": resume_json.get("first_name", "Не указано"),
                "Фамилия": resume_json.get("last_name", "Не указано"),
                "Отчество": resume_json.get("middle_name", "Не указано"),
                "Пол": resume_json.get("gender", {}).get("name", "Не указано"),
                "Возраст": resume_json.get("age", "Не указано"),
                "Желаемая ЗП": self._extract_salary(resume_json),
                "Должность": resume_json.get("title", "Не указана"),
                "Город": resume_json.get("area", {}).get("name", "Не указан"),
                "Опыт работы": self._flatten_experience(resume_json.get("experience", [])),
                "Ключевые навыки": ", ".join(resume_json.get("skill_set", [])) or "Не указаны",
                "Контакты": self._extract_contacts(resume_json),
                "Ссылка на резюме": resume_json.get("alternate_url", ""),
                "Обновлено": resume_json.get("updated_at", "").replace("T", " ").split(".")[0],
            }

            # Добавляем общее количество лет опыта, если доступно
            total_exp = resume_json.get("total_experience")
            if isinstance(total_exp, dict):
                months = total_exp.get("months", 0)
                years = months // 12
                result["Общий опыт (лет)"] = years
            else:
                result["Общий опыт (лет)"] = 0

            return result

        except Exception as e:
            log.error(f"[FORMAT] Ошибка при форматировании резюме: {e}", exc_info=True)
            raise

    def extract_experience_text(self, resume_json: Dict[str, Any]) -> str:
        """
        Извлекает текстовое описание опыта работы для последующего анализа через AI.

        Args:
            resume_json (Dict[str, Any]): raw резюме.

        Returns:
            str: объединённый текст всех описаний рабочих позиций.
        """
        try:
            descriptions = []
            for exp in resume_json.get("experience", []):
                desc = exp.get("description", "")
                if desc:
                    descriptions.append(desc)

            return "\n".join(descriptions)

        except Exception as e:
            log.warning(f"[AI] Не удалось извлечь опыт работы для AI: {e}")
            return ""

    def _flatten_experience(self, experience_list: List[Dict[str, Any]]) -> str:
        """
        Превращает массив опыта в читаемую строку.

        Args:
            experience_list (List[Dict[str, Any]]): список записей об опыте.

        Returns:
            str: строка типа "ООО Компания — 2 года".
        """
        try:
            lines = []
            for exp in experience_list:
                company = exp.get("company", "Без названия")
                position = exp.get("position", "Не указано")
                start = exp.get("start", "")[:4]
                end = exp.get("end", "")[:4] if exp.get("end") else "наст. время"
                line = f"{company} — {position} — {start}–{end}"
                lines.append(line)
            return "\n".join(lines)
        except Exception as e:
            log.warning(f"[FLATTEN] Ошибка при форматировании опыта: {e}")
            return "Ошибка форматирования"

    def _extract_contacts(self, resume_json: Dict[str, Any]) -> str:
        """
        Извлекает контактную информацию из резюме.

        Args:
            resume_json (Dict[str, Any]): raw резюме.

        Returns:
            str: строка с email и телефоном.
        """
        try:
            contact_info = []
            contacts = resume_json.get("contact", [])
            for contact in contacts:
                contact_type = contact.get("type", {}).get("name", "").lower()
                if contact_type == "эл. почта":
                    value = contact.get("value", "").strip()
                    if value:
                        contact_info.append(f"Email: {value}")
                elif "телефон" in contact_type:
                    value = contact.get("value", {}).get("formatted", "").strip()
                    if value:
                        contact_info.append(f"Телефон: {value}")

            return "\n".join(contact_info) if contact_info else "Нет контактов"
        except Exception as e:
            log.warning(f"[CONTACTS] Ошибка при извлечении контактов: {e}")
            return "Ошибка извлечения"

    def _extract_salary(self, resume_json: Dict[str, Any]) -> str:
        """
        Извлекает желаемую зарплату из резюме.

        Args:
            resume_json (Dict[str, Any]): raw резюме.

        Returns:
            str: строка вида "150 000 RUR".
        """
        salary = resume_json.get("salary")
        if not salary or not isinstance(salary, dict):
            return "Не указана"

        amount = salary.get("amount")
        currency = salary.get("currency", "")
        if amount is None:
            return "Не указана"

        return f"{amount} {currency}".strip()