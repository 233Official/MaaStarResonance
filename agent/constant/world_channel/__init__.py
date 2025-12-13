import json
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
CHANNEL_FILEPATH = CURRENT_DIR / "ChannelData.json"

with open(CHANNEL_FILEPATH, "r", encoding="utf-8") as f:
    CHANNEL_DATA = dict(json.load(f))

__all__ = ["CHANNEL_DATA"]
