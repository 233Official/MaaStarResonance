import json
from itertools import chain
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
FISH_FILEPATH = CURRENT_DIR / "FishData.json"

with open(FISH_FILEPATH, "r", encoding="utf-8") as f:
    FISH_DATA = json.load(f)

FISH_LIST = (lambda d: list(set(chain.from_iterable(chain.from_iterable(p.values() for p in d.values())))))(FISH_DATA)

__all__ = ["FISH_DATA"]
