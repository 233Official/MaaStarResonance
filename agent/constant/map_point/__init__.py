import json
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
MAP_POINT_FILEPATH = CURRENT_DIR / "MapPoint.json"
NAVIGATE_FILEPATH = CURRENT_DIR / "NavigatePoint.json"

with open(MAP_POINT_FILEPATH, "r", encoding="utf-8") as f:
    MAP_POINT_DATA = json.load(f)
with open(NAVIGATE_FILEPATH, "r", encoding="utf-8") as f:
    NAVIGATE_DATA = json.load(f)

__all__ = ["MAP_POINT_DATA", "NAVIGATE_DATA"]
