"""
Пакет `database` содержит всё, что связано с работой приложения с PostgreSQL через SQLAlchemy.

Модули:
    - base: базовый класс для всех моделей.
    - models: ORM-модели таблиц.
    - repository: реализация репозиториев для работы с данными.
    - session: настройки подключения к БД и фабрика сессий.

Exports:
    init_db: функция для инициализации таблиц в БД.
"""

from .base import Base
from .session import engine, SessionLocal
from .models import Resume, Task  # noqa


def init_db():
    """
    Инициализирует базу данных — создаёт все таблицы, если они ещё не существуют.

    Используется при запуске приложения для обеспечения наличия необходимых таблиц.
    """
    Base.metadata.create_all(bind=engine)