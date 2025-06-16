import requests
from typing import Tuple

def evaluate_candidate_match(candidate_exp: str, vacancy_description: str, api_key: str) -> Tuple[float, str]:
    """
    Сравнивает опыт кандидата с требованиями вакансии.
    
    Возвращает:
        - Процент соответствия (0–100)
        - Краткое объяснение (до 250 символов)
    """

    if not candidate_exp or not vacancy_description:
        return 0.0, "Недостаточно данных для анализа."

    prompt = f"""
Проанализируй опыт работы кандидата и оцени, насколько он соответствует следующей вакансии:

ВАКАНСИЯ:
{vacancy_description}

ОПЫТ КАНДИДАТА:
{candidate_exp}

ИНСТРУКЦИЯ:
- Верни только одно число (процент соответствия) и краткое заключение (до 250 символов).
- Не добавляй лишних слов или форматирования.
- Оценка должна быть строго по предоставленным данным.
- Заключение должно быть уникальным, лаконичным и понятным.

Пример ответа:
75 Кандидат имеет опыт приготовления блюд, но не указано знание выпечки в тандыре.
"""

    url = "https://api.deepseek.com/chat/completions" 
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 100
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        content = response.json()['choices'][0]['message']['content'].strip()

        # Парсим ответ
        parts = content.split(maxsplit=1)
        percent = float(parts[0].replace("%", "").strip())

        explanation = parts[1] if len(parts) > 1 else ""

        return round(percent, 1), explanation[:250]

    except Exception as e:
        print(f"[ERROR] Не удалось получить оценку: {e}")
        return 0.0, "Ошибка при оценке соответствия."