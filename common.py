"""Shared constants and helpers for notify.py and poll_command.py."""
import json
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).parent
KST = ZoneInfo("Asia/Seoul")


def load_json(path: Path, default=None):
    if default is not None and not path.exists():
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
