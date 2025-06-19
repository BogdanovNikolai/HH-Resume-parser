from typing import Callable, Optional, Dict, Any
from config import app_config

def execute_with_token(func: Callable[..., Optional[Dict]], *args, **kwargs) -> Optional[Dict]:
    """
    Выполняет переданную функцию с первым подходящим токеном.
    :param func: функция, принимающая access_token как первый аргумент
    :param args: дополнительные аргументы для func
    :param kwargs: дополнительные ключевые аргументы для func
    :return: результат выполнения func или None
    """
    access_tokens = app_config.get_access_tokens()
    if not access_tokens:
        print("[ERROR] Нет доступных токенов")
        return None

    for idx, token in enumerate(access_tokens):
        print(access_tokens)
        try:
            result = func(token, *args, **kwargs)
            if result:
                return result
        except Exception as e:
            print(f"[ERROR] Ошибка с токеном #{idx + 1}: {e}")
    return None