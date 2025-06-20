"""
Файл `main.py` — точка входа в приложение.

Запускает Flask-приложение из модуля `app`.

Functions:
    Нет функций верхнего уровня.
"""

import app
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()


if __name__ == "__main__":
    """
    Точка входа для запуска приложения.

    Запускает Flask-сервер с настройками:
        - host: 0.0.0.0 (доступен извне)
        - port: 5000
        - debug: False (режим продакшена)
    """
    app.app.run(host='0.0.0.0', port=5000, debug=False)