import os
import pandas as pd
import requests
from typing import List, Dict, Any, Optional
from utils.ai_evaluator import evaluate_candidate_match
from progress import progress_lock, global_progress


def prepare_resume_data(resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Преобразует одно резюме в нужный формат.
    Добавляет ключевые поля: опыт, зарплата, контакты и др.
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


def append_resumes_to_excel(
    resumes_data: Dict[str, Any],
    filename: str = "resumes_output.xlsx",
    description_input: str = "",
    deepseek_api_key: str = ""
) -> None:
    items = resumes_data.get("items", [])
    if not items:
        print("[INFO] Нет данных для записи.")
        return

    clean_data = []
    with progress_lock:
        global_progress["total_ai"] = len(items)

    for item in items:
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
        clean_data.append(resume_data)

        # === Увеличиваем AI-прогресс ===
        with progress_lock:
            global_progress["current_ai"] += 1

    df = pd.DataFrame(clean_data)
    try:
        df.to_excel(filename, index=False, engine='openpyxl')
        print(f"[SUCCESS] Успешно записано {len(df)} записей в '{filename}'")
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить файл: {e}")