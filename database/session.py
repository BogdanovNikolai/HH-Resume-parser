"""
Модуль `session` содержит настройки подключения к PostgreSQL и фабрику сессий SQLAlchemy.

Этот модуль обеспечивает централизованный доступ к базе данных через движок (engine) и фабрику сессий.
Также предоставляет зависимость `get_db()` для интеграции вне Flask-приложений.

Provides:
    engine: движок SQLAlchemy для работы с PostgreSQL.
    SessionLocal: фабрика сессий.
    get_db(): генератор сессии БД для использования вне Flask.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import app_config


# === Создание движка SQLAlchemy ===
engine = create_engine(
    f"postgresql://{app_config.DB_USER}:{app_config.DB_PASSWORD}"
    f"@{app_config.DB_HOST}:{app_config.DB_PORT}/{app_config.DB_NAME}"
)

# === Фабрика сессий ===
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# === Зависимость для получения сессии БД ===
def get_db():
    """
    Возвращает сессию базы данных для использования вне Flask-контекста.

    Yields:
        Session: объект сессии SQLAlchemy.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()