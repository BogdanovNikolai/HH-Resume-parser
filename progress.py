from threading import Lock

progress_lock = Lock()
global_progress = {
    "step": "hh",  # "hh" или "ai"
    "total_hh": 0,
    "current_hh": 0,
    "total_ai": 0,
    "current_ai": 0,
    "status": "ожидание",
    "filename": None
}