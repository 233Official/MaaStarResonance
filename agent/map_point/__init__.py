from pathlib import Path
import json

CURRENT_DIR = Path(__file__).parent
MAP_POINT_FILEPATH = CURRENT_DIR / "MapPoint.json"

with open(MAP_POINT_FILEPATH, "r", encoding="utf-8") as f:
    MAP_POINT_DATA = json.load(f)


__all__ = ["MAP_POINT_DATA"]
