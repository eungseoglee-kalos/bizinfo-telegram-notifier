"""Poll Telegram for a /list command, and also run the daily digest once a
day around 08:00 KST.

Both jobs ride on this one workflow's 5-minute schedule (see
.github/workflows/poll-command.yml) because GitHub silently never fired the
separate daily.yml schedule, while this one has fired reliably every time.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

import notify

TELEGRAM_GETUPDATES = "https://api.telegram.org/bot{token}/getUpdates"
OFFSET_PATH = Path(__file__).parent / "last_update_id.json"
COMMAND_TEXT = "/list"

# GitHub throttles this "every 5 minutes" schedule down to roughly every
# few hours in practice, so a single exact hour would risk being skipped
# entirely some days. Any poll tick landing in this window fires the digest.
DAILY_WINDOW_KST = range(7, 12)  # 07:00-11:59 KST
DAILY_STATE_PATH = Path(__file__).parent / "last_daily_run.json"


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


def handle_list_command(bot_token: str, api_key: str, allowed_chat_id: str) -> None:
    offset = load_offset()
    updates = get_updates(bot_token, offset)
    if not updates:
        print("No new messages.")
        return

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
        return

    notices = notify.fetch_notices(api_key)
    targeted = [n for n in notices if notify.is_target(n)]

    if not targeted:
        notify.send_telegram(bot_token, allowed_chat_id, "현재 조건에 맞는 지원사업이 없습니다.")
        print("Replied: no matching notices.")
        return

    header = f"📋 현재 전남 지원사업 전체 목록 ({len(targeted)}건)"
    for msg in notify.format_message(targeted, header=header):
        notify.send_telegram(bot_token, allowed_chat_id, msg)
    print(f"Replied with {len(targeted)} notice(s).")


def should_run_daily() -> bool:
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    if now_kst.hour not in DAILY_WINDOW_KST:
        return False
    last_run = ""
    if DAILY_STATE_PATH.exists():
        last_run = json.loads(DAILY_STATE_PATH.read_text(encoding="utf-8")).get("date", "")
    return last_run != now_kst.date().isoformat()


def mark_daily_run() -> None:
    today_kst = datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat()
    DAILY_STATE_PATH.write_text(json.dumps({"date": today_kst}), encoding="utf-8")


def main() -> int:
    api_key = os.environ["BIZINFO_API_KEY"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    allowed_chat_id = os.environ["TELEGRAM_CHAT_ID"]

    handle_list_command(bot_token, api_key, allowed_chat_id)

    if should_run_daily():
        print("Running daily digest...")
        notify.main()
        mark_daily_run()

    return 0


if __name__ == "__main__":
    sys.exit(main())
