"""
Модуль `base` содержит базовый класс для всех моделей SQLAlchemy.

Этот модуль используется Alembic для построения миграций. Все модели приложения должны наследоваться от Base.

Classes:
    Base: декларативная база SQLAlchemy, используемая для создания метаданных и миграций.
"""

from sqlalchemy.ext.declarative import declarative_base

# === Базовая модель для всех таблиц ===
Base = declarative_base()