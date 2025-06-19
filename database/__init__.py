from .base import Base
from .session import engine, SessionLocal
from .models import Resume, Task  # noqa

def init_db():
    """Создаёт все таблицы в БД."""
    Base.metadata.create_all(bind=engine)