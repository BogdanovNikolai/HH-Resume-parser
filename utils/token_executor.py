"""
Модуль `token_executor` содержит утилиты для выполнения функций с токенами доступа.

Основная функция:
    execute_with_token: выполняет переданную функцию с первым подходящим токеном из конфигурации.
"""

from typing import Callable, Optional, Dict, Any
from config import app_config


def execute_with_token(func: Callable[..., Optional[Dict]], *args, **kwargs) -> Optional[Dict]:
    """
    Выполняет переданную функцию с использованием доступных токенов.

    Пытается выполнить функцию с каждым токеном по очереди до первого успешного результата.
    
    Args:
        func (Callable[..., Optional[Dict]]): функция, принимающая access_token как первый аргумент.
        *args: дополнительные позиционные аргументы для передачи в func.
        **kwargs: дополнительные именованные аргументы для передачи в func.

    Returns:
        Optional[Dict]: результат выполнения функции или None, если все попытки завершились неудачей.

    Пример использования:
        >>> result = execute_with_token(get_company_vacancies, employer_id="123456")
        >>> print(result)
    """
    access_tokens = app_config.get_access_tokens()
    if not access_tokens:
        print("[ERROR] Нет доступных токенов")
        return None

    for idx, token in enumerate(access_tokens):
        try:
            result = func(token, *args, **kwargs)
            if result:
                return result
        except Exception as e:
            print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
    return None