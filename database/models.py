from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from .base import Base

class Resume(Base):
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