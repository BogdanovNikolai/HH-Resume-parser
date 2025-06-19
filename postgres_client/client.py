import psycopg2
import logging
from typing import Optional, Dict, Any
from config import app_config  # Импортируем глобальный экземпляр конфига

# Настройка логгирования
logger = logging.getLogger(__name__)

class PostgresClient:
    def __init__(self):
        """Инициализирует подключение к PostgreSQL."""
        try:
            self.conn = psycopg2.connect(
                dbname=app_config.DB_NAME,
                user=app_config.DB_USER,
                password=app_config.DB_PASSWORD,
                host=app_config.DB_HOST,
                port=app_config.DB_PORT
            )
            self.cur = self.conn.cursor()
            logger.info("Успешное подключение к PostgreSQL.")
        except Exception as e:
            logger.error(f"Не удалось подключиться к PostgreSQL: {e}")
            raise

    def init_progress(self, task_id: str) -> None:
        """Инициализирует прогресс задачи в PostgreSQL."""
        try:
            self.cur.execute("""
                INSERT INTO tasks (task_id, step, total_hh, current_hh, status)
                VALUES (%s, 'hh', 0, 0, 'ожидание')
            """, (task_id,))
            self.conn.commit()
            logger.debug(f"Прогресс инициализирован для task_id: {task_id}")
        except Exception as e:
            logger.error(f"Ошибка при инициализации прогресса для task_id {task_id}: {e}")
            self.conn.rollback()

    def update_progress(self, task_id: str, field: str, value: Any) -> None:
        """Обновляет конкретное поле прогресса в PostgreSQL."""
        try:
            query = f"UPDATE tasks SET {field} = %s WHERE task_id = %s"
            self.cur.execute(query, (value, task_id))
            self.conn.commit()
            logger.debug(f"Поле '{field}' обновлено для task_id: {task_id}")
        except Exception as e:
            logger.error(f"Ошибка при обновлении поля '{field}' для task_id {task_id}: {e}")
            self.conn.rollback()

    def get_progress(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Получает прогресс задачи из PostgreSQL."""
        try:
            self.cur.execute("SELECT * FROM tasks WHERE task_id = %s", (task_id,))
            result = self.cur.fetchone()
            if not result:
                logger.warning(f"Прогресс для task_id {task_id} не найден.")
                return None
            columns = [desc[0] for desc in self.cur.description]
            return dict(zip(columns, result))
        except Exception as e:
            logger.error(f"Ошибка при получении прогресса для task_id {task_id}: {e}")
            return None

    def increment_progress(self, task_id: str, field: str, delta: int = 1) -> None:
        """Увеличивает значение поля прогресса на delta."""
        try:
            self.cur.execute(f"UPDATE tasks SET {field} = {field} + %s WHERE task_id = %s", (delta, task_id))
            self.conn.commit()
            logger.debug(f"Поле '{field}' увеличено на {delta} для task_id: {task_id}")
        except Exception as e:
            logger.error(f"Ошибка при инкременте поля '{field}' для task_id {task_id}: {e}")
            self.conn.rollback()

    def delete_progress(self, task_id: str) -> None:
        """Удаляет прогресс задачи из PostgreSQL."""
        try:
            self.cur.execute("DELETE FROM tasks WHERE task_id = %s", (task_id,))
            self.conn.commit()
            logger.debug(f"Прогресс для task_id {task_id} удален.")
        except Exception as e:
            logger.error(f"Ошибка при удалении прогресса для task_id {task_id}: {e}")
            self.conn.rollback()

    def create_tables(self) -> None:
        """Создает таблицы, если они не существуют."""
        try:
            self.cur.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    step TEXT,
                    total_hh INTEGER,
                    current_hh INTEGER,
                    total_ai INTEGER,
                    current_ai INTEGER,
                    status TEXT,
                    filename TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()
            logger.info("Таблицы успешно созданы или уже существуют.")
        except Exception as e:
            logger.error(f"Ошибка при создании таблиц: {e}")
            self.conn.rollback()

    def close(self) -> None:
        """Закрывает соединение с PostgreSQL."""
        if hasattr(self, 'cur'):
            self.cur.close()
        if hasattr(self, 'conn'):
            self.conn.close()
        logger.info("Соединение с PostgreSQL закрыто.")