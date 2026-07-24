"""Fetch new 기업마당(bizinfo.go.kr) support-program notices scoped to 전남
(전남, 전남광주, or multi-region collaborations that include 전남광주), and
push the new ones to Telegram.

Called once a day (when due) by bot_daemon.py's always-on loop. Also shared
by poll_command.py, which answers the /list command with the full current
list.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date, datetime, timedelta

import requests

from common import BASE_DIR, load_json, save_json

BIZINFO_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

STATE_PATH = BASE_DIR / "sent_ids.json"
STATE_RETENTION_DAYS = 120
FETCH_COUNT = 100
TELEGRAM_MSG_LIMIT = 4000

TARGET_REGION = "전남광주"
REGION_CODES = {
    "서울", "부산", "대구", "인천", "전남광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "경북", "경남", "제주",
}

# bizinfo only has one merged "전남광주" hashtag, but titles sub-label which
# half it's actually for ([전남], [광주], or [전남광주]). Only 광주-only
# notices are out of scope.
TITLE_TAG_RE = re.compile(r"^\[([^\]]+)\]")
EXCLUDED_TITLE_TAGS = {"광주"}


def fetch_notices(api_key: str) -> list[dict]:
    resp = requests.get(
        BIZINFO_URL,
        params={"crtfcKey": api_key, "dataType": "json", "searchCnt": FETCH_COUNT},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("jsonArray", [])


def is_target(notice: dict) -> bool:
    title_match = TITLE_TAG_RE.match(notice.get("pblancNm", ""))
    if title_match and title_match.group(1) in EXCLUDED_TITLE_TAGS:
        return False  # 광주 단독 표기 제외

    tags = {t.strip() for t in notice.get("hashtags", "").split(",")} & REGION_CODES
    if not tags or tags == REGION_CODES:
        return False  # 지역 태그 없음(전국) 또는 전 지역 태그(전국) => 제외

    return TARGET_REGION in tags  # 단일/다지역 협업 모두, 전남광주 포함 시만 채택


def load_state() -> dict[str, str]:
    return load_json(STATE_PATH, {})


def save_state(state: dict[str, str]) -> None:
    cutoff = date.today() - timedelta(days=STATE_RETENTION_DAYS)
    pruned = {
        pid: seen for pid, seen in state.items()
        if datetime.strptime(seen, "%Y-%m-%d").date() >= cutoff
    }
    save_json(STATE_PATH, pruned)


def format_message(notices: list[dict], header: str | None = None) -> list[str]:
    header = header or f"📋 기업마당 신규 지원사업 ({len(notices)}건)"
    lines = [header + "\n"]
    for n in notices:
        title = n.get("pblancNm", "(제목 없음)")
        period = n.get("reqstBeginEndDe", "기간 정보 없음")
        org = n.get("jrsdInsttNm", "")
        url = n.get("pblancUrl", "")
        lines.append(f"• {title}\n  {org} | {period}\n  {url}\n")

    messages, current = [], lines[0]
    for line in lines[1:]:
        if len(current) + len(line) > TELEGRAM_MSG_LIMIT:
            messages.append(current)
            current = line
        else:
            current += "\n" + line
    messages.append(current)
    return messages


def send_telegram(token: str, chat_id: str, text: str) -> None:
    resp = requests.post(
        TELEGRAM_API.format(token=token),
        json={
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    resp.raise_for_status()


def main() -> int:
    api_key = os.environ["BIZINFO_API_KEY"]
    bot_token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]

    notices = fetch_notices(api_key)
    targeted = [n for n in notices if is_target(n)]

    state = load_state()
    today = date.today().isoformat()
    new_notices = [n for n in targeted if n.get("pblancId") not in state]

    if new_notices:
        for msg in format_message(new_notices):
            send_telegram(bot_token, chat_id, msg)
        print(f"Sent {len(new_notices)} new notice(s).")
    else:
        print("No new notices today.")

    for n in targeted:
        state.setdefault(n["pblancId"], today)
    save_state(state)
    return 0


if __name__ == "__main__":
    sys.exit(main())
