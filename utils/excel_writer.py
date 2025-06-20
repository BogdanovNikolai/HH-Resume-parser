"""
Модуль `excel_writer` содержит утилиты для подготовки данных о резюме и сохранения их в формате Excel (.xlsx).

Основные возможности:
- безопасное извлечение вложенных данных через `safe_get`,
- подготовка данных о резюме для отображения,
- запись результатов в Excel с поддержкой AI-оценки соответствия.

Functions:
    safe_get: безопасно извлекает значение по цепочке ключей.
    prepare_resume_data: преобразует raw данные резюме в удобный формат.
    save_resumes_to_excel: сохраняет список резюме в Excel, с возможностью AI-анализа.
"""

import pandas as pd
from typing import List, Dict, Any, Union, Callable
from functools import reduce

# === Внешние зависимости ===
from utils.ai_evaluator import evaluate_candidate_match
from redis_client import redis_client


def safe_get(data: Any, *keys: Union[str, int, Callable], default: Any = "Не указано") -> Any:
    """
    Безопасно извлекает значение из вложенных словарей/списков по цепочке ключей.

    Примеры:
        safe_get(resume, 'first_name') → "Иван"
        safe_get(resume, 'gender', 'name') → "Мужской"
        safe_get(resume, 'experience', 0, 'company') → "DHL Express"
        safe_get(resume, 'salary', 'amount', default=0) → 1500
        safe_get(resume, 'area', 'name', default="Не указан") → "Москва"

    Args:
        data (Any): исходные данные (dict, list, object).
        keys (Union[str, int, Callable]): последовательность ключей или индексов для извлечения.
        default (Any): значение по умолчанию, если путь не найден.

    Returns:
        Any: значение по цепочке ключей или default.
    """
    def _get_value(current: Any, key: Union[str, int, Callable]) -> Any:
        if isinstance(key, str):
            return current.get(key) if isinstance(current, dict) else None
        elif isinstance(key, int):
            return current[key] if isinstance(current, list) and len(current) > key else None
        elif callable(key):
            return key(current)
        else:
            return None

    result = reduce(_get_value, keys, data)
    return result if result is not None else default


def prepare_resume_data(resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Преобразует одно резюме в нужный формат.

    Добавляет ключевые поля: опыт, зарплата, контакты и другие метаданные.

    Args:
        resume (Dict[str, Any]): сырое резюме из API HeadHunter.

    Returns:
        Dict[str, Any]: структурированное представление резюме.
    """
    title = resume.get("title", "Не указана")

    area = resume.get("area", {})
    region = area.get("name", "") if isinstance(area, dict) else "Не указан"

    age = resume.get("age") or "Не указан"
    gender = resume.get("gender", {}).get("name", "Не указан")

    experience = resume.get("experience", [])
    total_experience = resume.get("total_experience", {})
    total_years = total_experience.get("months", 0) // 12 if isinstance(total_experience, dict) else 0

    # === Подготавливаем опыт работы ===
    experience_list = []
    for exp in experience:
        company = exp.get("company", "Без названия")
        start = exp.get("start", "").split("-")[0]
        end = exp.get("end", "").split("-")[0] if exp.get("end") else "наст. время"
        description = exp.get("description", "")
        try:
            years = int(end) - int(start[:4])
        except Exception:
            years = "?"
        experience_line = f"{company} — {years} лет"
        if description:
            experience_line += f"\n{description}"
        experience_list.append(experience_line)

    experience_str = "\n\n".join(experience_list)

    salary = resume.get("salary")
    salary_expectation = None
    if salary and isinstance(salary, dict):
        amount = salary.get("amount", "")
        currency = salary.get("currency", "")
        salary_expectation = f"{amount} {currency}".strip() or None

    professional_roles = [role.get("name", "") for role in resume.get("professional_roles", [])]
    professional_roles_str = ", ".join(professional_roles) or "Не указаны"

    skill_set = resume.get("skill_set", [])
    skills = ", ".join(skill_set) if skill_set else "Не указаны"

    contact_info = []
    contacts = resume.get("contact", [])
    for contact in contacts:
        contact_type = contact.get("type", {}).get("name", "").lower()
        if contact_type == "эл. почта":
            email = contact.get("value", "").strip()
            if email:
                contact_info.append(f"Email: {email}")
        elif "телефон" in contact_type:
            value = contact.get("value", {})
            formatted_phone = value.get("formatted", "").strip()
            if formatted_phone:
                contact_info.append(f"Телефон: {formatted_phone}")

    contact_str = "\n".join(contact_info) if contact_info else "Нет доступных контактов"
    resume_link = resume.get("alternate_url", "") or resume.get("url", "")

    return {
        "Позиция": title,
        "Регион": region,
        "Возраст": age,
        "Пол": gender,
        "Общий опыт работы (лет)": total_years,
        "Опыт работы по компаниям": experience_str,
        "Желаемая зарплата": salary_expectation,
        "Профессиональные роли": professional_roles_str,
        "Ключевые навыки": skills,
        "Контакты": contact_str,
        "Ссылка на резюме": resume_link
    }


def save_resumes_to_excel(
    items: List[Dict],
    filename: str = "resumes_output.xlsx",
    description_input: str = "",
    deepseek_api_key: str = "",
    task_id: str = None,
    is_new: bool = False
):
    """
    Сохраняет список резюме в Excel-файл.

    Может также добавлять оценку соответствия вакансии при наличии описания и API-ключа.

    Args:
        items (List[Dict]): список резюме.
        filename (str): имя выходного файла.
        description_input (str): описание вакансии для анализа.
        deepseek_api_key (str): ключ к DeepSeek API.
        task_id (Optional[str]): ID задачи для обновления прогресса в Redis.
        is_new (bool): флаг новых резюме из HH API.
    """
    if not items:
        print("[INFO] Нет данных для записи.")
        return

    clean_data = []

    # === Если есть task_id — инициализируем шаг AI и total_ai в Redis ===
    if task_id:
        redis_client.update_progress(task_id, "step", "ai")
        redis_client.update_progress(task_id, "total_ai", len(items))

    for idx, item in enumerate(items):
        if is_new:
            resume = safe_get(item, "resume", default={})
            if not isinstance(resume, dict):
                print(f"[WARNING] Пропущено: резюме не является словарём — {resume}")
                continue

            # --- Имя, фамилия, отчество ---
            first_name = safe_get(resume, "first_name")
            last_name = safe_get(resume, "last_name")
            middle_name = safe_get(resume, "middle_name")

            # --- Пол ---
            gender_name = safe_get(resume, "gender", "name")

            # --- Возраст ---
            age = safe_get(resume, "age")

            # --- Должность ---
            title = safe_get(resume, "title")

            # --- Город ---
            area_name = safe_get(resume, "area", "name")

            # --- Зарплата ---
            salary_amount = safe_get(resume, "salary", "amount")
            salary_currency = safe_get(resume, "salary", "currency")
            salary_expectation = f"{salary_amount} {salary_currency}".strip() or "Не указана"

            # --- Опыт работы ---
            experience_list = safe_get(resume, "experience", default=[])
            experience_str = "\n".join([
                f"{safe_get(exp, 'company', default='Без названия')} — "
                f"{safe_get(exp, 'position')} — "
                f"{safe_get(exp, 'start', default='').split('-')[0]} — "
                f"{safe_get(exp, 'end', default='').split('-')[0] if safe_get(exp, 'end') else 'наст. время'}"
                for exp in experience_list
            ]) or "Нет опыта"

            # --- Ключевые навыки ---
            skill_set = safe_get(resume, "skill_set", default=[])
            skills = ", ".join(skill_set) if isinstance(skill_set, list) and skill_set else "Не указаны"

            # --- Ссылка на резюме ---
            alternate_url = safe_get(resume, "alternate_url")

            # --- Время обновления ---
            updated_at = safe_get(resume, "updated_at")

            row = {
                "ID Резюме": safe_get(resume, "id"),
                "Имя": first_name,
                "Фамилия": last_name,
                "Отчество": middle_name,
                "Пол": gender_name,
                "Возраст": age,
                "Желаемая ЗП": salary_expectation,
                "Должность": title,
                "Город": area_name,
                "Опыт работы": experience_str,
                "Ключевые навыки": skills,
                "Ссылка": alternate_url,
                "Обновлено": updated_at
            }
        else:
            resume_data = prepare_resume_data(item)
            candidate_exp = "\n".join([
                exp.get("description", "") for exp in item.get("experience", [])
            ])

            match_percent = None
            explanation = "Не оценивалось"
            if description_input and deepseek_api_key and candidate_exp:
                match_percent, explanation = evaluate_candidate_match(candidate_exp, description_input, deepseek_api_key)

            resume_data["Соответствие (%)"] = match_percent
            resume_data["Заключение"] = explanation
            row = resume_data

        clean_data.append(row)

        # === Увеличиваем AI-прогресс в Redis ===
        if task_id:
            redis_client.increment_progress(task_id, "current_ai")

    df = pd.DataFrame(clean_data)
    try:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"[SUCCESS] Успешно записано {len(df)} записей в '{filename}'")
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить файл: {e}")