import os
import pandas as pd
from typing import List, Dict, Any, Optional


def prepare_resume_data(resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Преобразует одно резюме в нужный формат.
    Скрывает ФИО, добавляет контакты, навыки и другие поля.
    """

    # === ФИО (пока не используется) ===
    full_name = "Не указано"

    # === Позиция ===
    title = resume.get("title", "Не указана")

    # === Регион ===
    area = resume.get("area", {})
    region = area.get("name", "") if isinstance(area, dict) else "Не указан"

    # === Возраст ===
    age = resume.get("age") or "Не указан"

    # === Пол ===
    gender = resume.get("gender", {}).get("name", "Не указан")

    # === Опыт работы ===
    experience = resume.get("experience", [])
    total_experience = resume.get("total_experience", {})
    total_years = total_experience.get("months", 0) // 12 if isinstance(total_experience, dict) else 0

    # === Опыт по компаниям ===
    experience_list = []
    for exp in experience:
        company = exp.get("company", "Без названия")
        start = exp.get("start", "").split("-")[0]
        end = exp.get("end", "").split("-")[0] if exp.get("end") else "наст. время"

        try:
            years = int(end) - int(start[:4])
        except Exception:
            years = "?"

        experience_list.append(f"{company} — {years} лет")

    experience_str = "\n".join(experience_list)

    # === Зарплата ===
    salary = resume.get("salary")
    salary_expectation = None
    if salary and isinstance(salary, dict):
        amount = salary.get("amount", "")
        currency = salary.get("currency", "")
        salary_expectation = f"{amount} {currency}".strip() or None

    # === Профессиональные роли ===
    professional_roles = [role.get("name", "") for role in resume.get("professional_roles", [])]
    professional_roles_str = ", ".join(professional_roles) or "Не указаны"

    # === Навыки ===
    skill_set = resume.get("skill_set", [])
    skills = ", ".join(skill_set) if skill_set else "Не указаны"

    # === Контакты ===
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

    # === Ссылка на резюме ===
    resume_link = resume.get("alternate_url", "")
    if not resume_link:
        resume_link = resume.get("url", "")

    return {
        "ФИО": full_name,
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


def append_resumes_to_excel(
    resumes_data: Dict[str, Any],
    filename: str = "resumes_output.xlsx"
) -> None:
    """
    Записывает данные о резюме в Excel-файл с красивой структурой.

    Аргументы:
        resumes_data (dict): Ответ от findResumes()
        filename (str): Имя файла для сохранения
    """
    items = resumes_data.get("items", [])

    if not items:
        print("[INFO] Нет данных для записи.")
        return

    # Подготавливаем данные
    clean_data = [prepare_resume_data(item) for item in items]

    # Создаём DataFrame
    df = pd.DataFrame(clean_data)

    # Сохраняем в Excel
    try:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"[SUCCESS] Успешно записано {len(df)} записей в '{filename}'")
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить файл: {e}")