"""
Модуль `repository` содержит класс DatabaseRepository — реализацию репозитория для работы с БД через SQLAlchemy.

Класс предоставляет методы для сохранения, загрузки и обновления данных о резюме и задачах.

Classes:
    DatabaseRepository: класс, предоставляющий CRUD-операции над данными.
"""

from sqlalchemy.orm import Session
from .models import Resume


class DatabaseRepository:
    """
    Класс репозитория для работы с базой данных.

    Предоставляет методы для взаимодействия с таблицами `resumes` и `tasks`.
    
    Attributes:
        db (Session): активная сессия SQLAlchemy.
    """

    def __init__(self, db: Session):
        """
        Инициализирует репозиторий с активной сессией БД.

        Args:
            db (Session): сессия SQLAlchemy.
        """
        self.db = db

    def save_resumes(self, task_id: str, resumes: list[dict]) -> None:
        """
        Сохраняет или обновляет список резюме в БД.

        Args:
            task_id (str): идентификатор задачи.
            resumes (list[dict]): список словарей с данными о резюме.
        """
        for resume_data in resumes:
            resume = Resume(**resume_data, task_id=task_id)
            self.db.merge(resume)  # upsert
        self.db.commit()

    def load_resumes_by_task(self, task_id: str) -> list[Resume]:
        """
        Загружает все резюме, связанные с указанной задачей.

        Args:
            task_id (str): идентификатор задачи.

        Returns:
            list[Resume]: список объектов Resume.
        """
        return self.db.query(Resume).filter(Resume.task_id == task_id).all()

    def load_resumes_by_vacancy(self, vacancy_id: str) -> list[Resume]:
        """
        Загружает все резюме, найденные по указанной вакансии.

        Args:
            vacancy_id (str): ID вакансии.

        Returns:
            list[Resume]: список объектов Resume.
        """
        return self.db.query(Resume).filter(Resume.vacancy_id == vacancy_id).all()

    def update_resume_match(self, resume_id: str, match_percent: float, explanation: str) -> None:
        """
        Обновляет оценку соответствия резюме вакансии.

        Args:
            resume_id (str): ID резюме.
            match_percent (float): процент соответствия.
            explanation (str): объяснение AI-оценки.
        """
        resume = self.db.query(Resume).filter(Resume.resume_id == resume_id).first()
        if resume:
            resume.match_percent = match_percent
            resume.explanation = explanation
            self.db.commit()

    def get_task_resumes_count(self, task_id: str) -> int:
        """
        Возвращает количество резюме, связанных с указанной задачей.

        Args:
            task_id (str): идентификатор задачи.

        Returns:
            int: количество резюме.
        """
        return self.db.query(Resume).filter(Resume.task_id == task_id).count()