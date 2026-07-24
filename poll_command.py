"""Handle the /list command: reply with every currently-open 전남 support
program notice (not just new ones).

Called every loop iteration by bot_daemon.py. get_updates() long-polls for
up to TELEGRAM_POLL_TIMEOUT seconds, so a command gets an answer almost
immediately instead of waiting on a fixed schedule.
"""
from __future__ import annotations

import os

import requests

import notify
from common import BASE_DIR, load_json, save_json

TELEGRAM_GETUPDATES = "https://api.telegram.org/bot{token}/getUpdates"
OFFSET_PATH = BASE_DIR / "last_update_id.json"
COMMAND_TEXT = "/list"


def get_updates(token: str, offset: int) -> list[dict]:
    poll_timeout = int(os.environ.get("TELEGRAM_POLL_TIMEOUT", "0"))
    resp = requests.get(
        TELEGRAM_GETUPDATES.format(token=token),
        params={"offset": offset, "timeout": poll_timeout},
        timeout=max(poll_timeout + 10, 15),
    )
    resp.raise_for_status()
    return resp.json()["result"]


def main() -> None:
    api_key = os.environ["BIZINFO_API_KEY"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    allowed_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    offset = load_json(OFFSET_PATH, {"offset": 0})["offset"]
    updates = get_updates(bot_token, offset)
    if not updates:
        return

    should_reply = False
    for u in updates:
        offset = max(offset, u["update_id"] + 1)
        message = u.get("message") or {}
        text = (message.get("text") or "").strip()
        chat_id = str(message.get("chat", {}).get("id", ""))
        if text == COMMAND_TEXT and chat_id == allowed_chat_id:
            should_reply = True
    save_json(OFFSET_PATH, {"offset": offset})

    if not should_reply:
        return

    notices = notify.fetch_notices(api_key)
    targeted = [n for n in notices if notify.is_target(n)]

    if not targeted:
        notify.send_telegram(bot_token, allowed_chat_id, "현재 조건에 맞는 지원사업이 없습니다.")
        print("Replied: no matching notices.", flush=True)
        return

    header = f"📋 현재 전남 지원사업 전체 목록 ({len(targeted)}건)"
    for msg in notify.format_message(targeted, header=header):
        notify.send_telegram(bot_token, allowed_chat_id, msg)
    print(f"Replied with {len(targeted)} notice(s).", flush=True)


if __name__ == "__main__":
    main()
