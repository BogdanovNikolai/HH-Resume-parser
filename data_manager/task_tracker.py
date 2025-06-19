from typing import Dict, Optional
from redis_client import redis_client
from config import log

class TaskTracker:
    def update_step(self, task_id: str, step: str):
        redis_client.update_progress(task_id, "step", step)

    def set_status(self, task_id: str, status: str):
        redis_client.update_progress(task_id, "status", status)

    def set_total_ai(self, task_id: str, total_ai: int):
        redis_client.update_progress(task_id, "total_ai", total_ai)

    def increment_current_ai(self, task_id: str):
        redis_client.increment_progress(task_id, "current_ai")

    def set_filename(self, task_id: str, filename: str):
        redis_client.update_progress(task_id, "filename", filename)

    def get_progress(self, task_id: str) -> Optional[Dict]:
        return redis_client.get_progress(task_id)