from pathlib import Path
import json

CURRENT_DIR = Path(__file__).parent
ANDROID_KEY_EVENT_FILEPATH = CURRENT_DIR / "AndroidKeyEvent.json"

with open(ANDROID_KEY_EVENT_FILEPATH, "r", encoding="utf-8") as f:
    ANDROID_KEY_EVENT_DATA = json.load(f)


__all__ = ["ANDROID_KEY_EVENT_DATA"]
