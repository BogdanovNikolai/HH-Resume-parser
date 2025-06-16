import requests
from typing import List, Dict, Any

def get_hh_areas() -> List[Dict[str, Any]]:
    """
    Загружает список всех регионов и городов с HeadHunter API.
    Возвращает дерево регионов.
    """
    url = "https://api.hh.ru/areas" 
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()

    return data  # Это список регионов с вложенными городами