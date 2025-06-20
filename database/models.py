"""
Модуль `models` содержит SQLAlchemy-модели для работы с базой данных PostgreSQL.

Эти модели используются как для ORM-операций, так и для генерации миграций через Alembic.

Classes:
    Resume: модель для хранения данных о резюме.
    Task: модель для отслеживания фоновых задач и их прогресса.
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base


class Resume(Base):
    """
    Модель для хранения информации о резюме.

    Attributes:
        id (Integer): уникальный ID записи.
        resume_id (String): ID резюме из HeadHunter.
        first_name (String): имя соискателя.
        last_name (String): фамилия соискателя.
        middle_name (String): отчество соискателя.
        gender (String): пол.
        age (Integer): возраст.
        salary (String): желаемая зарплата.
        title (String): должность.
        area (String): город проживания.
        experience (Text): опыт работы (форматированный).
        skills (Text): ключевые навыки.
        contacts (Text): контактная информация.
        link (String): ссылка на резюме.
        updated_at (DateTime): дата последнего обновления резюме.
        match_percent (Float): процент соответствия вакансии.
        explanation (Text): объяснение AI-оценки.
        total_experience (Integer): общий опыт в годах.
        task_id (String): внешний ключ на задачу.
        vacancy_id (String): ID вакансии, по которой найдено резюме.
        created_at (DateTime): дата создания записи.

    Relationships:
        task: связь с моделью Task.
    """

    __tablename__ = 'resumes'

    id = Column(Integer, primary_key=True)
    resume_id = Column(String, unique=True, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    middle_name = Column(String)
    gender = Column(String)
    age = Column(Integer)
    salary = Column(String)
    title = Column(String)
    area = Column(String)
    experience = Column(Text)
    skills = Column(Text)
    contacts = Column(Text)
    link = Column(String)
    updated_at = Column(DateTime)
    match_percent = Column(Float)
    explanation = Column(Text)
    total_experience = Column(Integer)
    task_id = Column(String, ForeignKey('tasks.task_id', ondelete='CASCADE'))
    vacancy_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="resumes")

    def to_dict(self):
        """
        Преобразует объект Resume в словарь.

        Returns:
            Dict[str, Any]: представление резюме в виде словаря.
        """
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "middle_name": self.middle_name,
            "gender": self.gender,
            "age": self.age,
            "salary": self.salary,
            "title": self.title,
            "area": self.area,
            "experience": self.experience,
            "skills": self.skills,
            "contacts": self.contacts,
            "link": self.link,
            "updated_at": self.updated_at,
            "match_percent": self.match_percent,
            "explanation": self.explanation,
            "total_experience": self.total_experience,
            "task_id": self.task_id,
            "vacancy_id": self.vacancy_id,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Task(Base):
    """
    Модель для отслеживания фоновых задач.

    Attributes:
        task_id (String): уникальный идентификатор задачи.
        step (String): текущий этап выполнения ('hh', 'ai').
        total_hh (Integer): общее количество найденных резюме.
        current_hh (Integer): количество уже обработанных резюме.
        total_ai (Integer): количество резюме для оценки AI.
        current_ai (Integer): количество уже оценённых резюме.
        status (String): статус задачи ('в процессе', 'готово', 'ошибка').
        filename (String): имя выходного файла после экспорта.
        created_at (DateTime): дата создания задачи.

    Relationships:
        resumes: связь с моделью Resume.
    """

    __tablename__ = 'tasks'

    task_id = Column(String, primary_key=True)
    step = Column(String)
    total_hh = Column(Integer)
    current_hh = Column(Integer)
    total_ai = Column(Integer)
    current_ai = Column(Integer)
    status = Column(String)
    filename = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="task")