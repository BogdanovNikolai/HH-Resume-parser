from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import app_config

# Создаём движок
engine = create_engine(
    f"postgresql://{app_config.DB_USER}:{app_config.DB_PASSWORD}@{app_config.DB_HOST}:{app_config.DB_PORT}/{app_config.DB_NAME}"
)

# Фабрика сессий
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Для удобства использования вне Flask
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()