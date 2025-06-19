from sqlalchemy.orm import Session
from .models import Resume


class DatabaseRepository:
    def __init__(self, db: Session):
        self.db = db

    def save_resumes(self, task_id: str, resumes: list[dict]) -> None:
        for resume_data in resumes:
            resume = Resume(**resume_data, task_id=task_id)
            self.db.merge(resume)  # upsert
        self.db.commit()

    def load_resumes_by_task(self, task_id: str) -> list[Resume]:
        return self.db.query(Resume).filter(Resume.task_id == task_id).all()

    def load_resumes_by_vacancy(self, vacancy_id: str) -> list[Resume]:
        return self.db.query(Resume).filter(Resume.vacancy_id == vacancy_id).all()

    def update_resume_match(self, resume_id: str, match_percent: float, explanation: str) -> None:
        resume = self.db.query(Resume).filter(Resume.resume_id == resume_id).first()
        if resume:
            resume.match_percent = match_percent
            resume.explanation = explanation
            self.db.commit()

    def get_task_resumes_count(self, task_id: str) -> int:
        return self.db.query(Resume).filter(Resume.task_id == task_id).count()