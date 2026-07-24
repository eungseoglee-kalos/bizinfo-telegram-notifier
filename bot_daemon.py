#!/usr/bin/env python3
"""Always-on daemon for the server deploy (Docker), replacing GitHub Actions cron.

Combines two things into one persistent process:
  - Telegram /list command handling via long-polling (near-instant, no wait)
  - The daily 전남 digest, run once per day after DAILY_CHECK_AFTER (KST)

Both reuse the exact same logic as poll_command.py / notify.py -- this file
only adds the loop and the "has today's digest already run" bookkeeping.
"""
import time
from datetime import datetime

import notify
import poll_command
from common import BASE_DIR, KST, load_json, save_json

LAST_DAILY_RUN_PATH = BASE_DIR / "last_daily_run.json"
DAILY_CHECK_AFTER = (8, 0)  # (hour, minute) KST
IDLE_RETRY_SECONDS = 5  # pause after an unexpected error before looping again


def run_daily_digest_if_due() -> None:
    last = load_json(LAST_DAILY_RUN_PATH, {"date": None})
    now = datetime.now(KST)
    today = now.date().isoformat()

    if last["date"] == today or (now.hour, now.minute) < DAILY_CHECK_AFTER:
        return

    notify.main()
    save_json(LAST_DAILY_RUN_PATH, {"date": today})
    print(f"[{now.isoformat()}] daily digest done", flush=True)


def main() -> None:
    print("bizinfo-telegram-notifier daemon started", flush=True)
    while True:
        try:
            poll_command.main()  # blocks up to TELEGRAM_POLL_TIMEOUT seconds when idle
            run_daily_digest_if_due()
        except Exception as exc:  # keep the daemon alive across transient network errors
            print(f"error in daemon loop: {exc}", flush=True)
            time.sleep(IDLE_RETRY_SECONDS)


if __name__ == "__main__":
    main()
