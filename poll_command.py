"""Poll Telegram for a /list command and, when seen, reply with every
currently-open 전남 support-program notice (not just new ones).

Run every few minutes via GitHub Actions (see .github/workflows/poll-command.yml).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests

import notify

TELEGRAM_GETUPDATES = "https://api.telegram.org/bot{token}/getUpdates"
OFFSET_PATH = Path(__file__).parent / "last_update_id.json"
COMMAND_TEXT = "/list"


def load_offset() -> int:
    if not OFFSET_PATH.exists():
        return 0
    return json.loads(OFFSET_PATH.read_text(encoding="utf-8"))["offset"]


def save_offset(offset: int) -> None:
    OFFSET_PATH.write_text(json.dumps({"offset": offset}), encoding="utf-8")


def get_updates(token: str, offset: int) -> list[dict]:
    resp = requests.get(
        TELEGRAM_GETUPDATES.format(token=token),
        params={"offset": offset, "timeout": 0},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["result"]


def main() -> int:
    api_key = os.environ["BIZINFO_API_KEY"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    allowed_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    offset = load_offset()
    updates = get_updates(bot_token, offset)

    if not updates:
        print("No new messages.")
        return 0

    should_reply = False
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        message = u.get("message") or {}
        text = (message.get("text") or "").strip()
        chat_id = str(message.get("chat", {}).get("id", ""))
        if text == COMMAND_TEXT and chat_id == allowed_chat_id:
            should_reply = True

    save_offset(offset)

    if not should_reply:
        print("No /list command from the authorized chat.")
        return 0

    notices = notify.fetch_notices(api_key)
    targeted = [n for n in notices if notify.is_target(n)]

    if not targeted:
        notify.send_telegram(bot_token, allowed_chat_id, "현재 조건에 맞는 지원사업이 없습니다.")
        print("Replied: no matching notices.")
        return 0

    header = f"📋 현재 전남 지원사업 전체 목록 ({len(targeted)}건)"
    for msg in notify.format_message(targeted, header=header):
        notify.send_telegram(bot_token, allowed_chat_id, msg)
    print(f"Replied with {len(targeted)} notice(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
