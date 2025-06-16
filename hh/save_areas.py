from areas import get_hh_areas
import json

areas = get_hh_areas()
with open("utils/areas_cache.json", "w", encoding="utf-8") as f:
    json.dump(areas, f, ensure_ascii=False, indent=2)
print("[SUCCESS] Регионы сохранены в utils/areas_cache.json")