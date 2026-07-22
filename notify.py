"""Fetch new 기업마당(bizinfo.go.kr) support-program notices for 전남광주 and
nationwide items, and push the new ones to Telegram.

Run daily via GitHub Actions (see .github/workflows/daily.yml).
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import requests

BIZINFO_URL = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

STATE_PATH = Path(__file__).parent / "sent_ids.json"
STATE_RETENTION_DAYS = 120
FETCH_COUNT = 100
TELEGRAM_MSG_LIMIT = 4000

TARGET_REGION = "전남광주"
REGION_CODES = {
    "서울", "부산", "대구", "인천", "전남광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "경북", "경남", "제주",
}
# jrsdInsttNm for a province/metro government always ends in one of these;
# central ministries end in 부/처/청 and never match. 전남광주통합특별시 also
# ends in 특별시, so it needs an explicit carve-out below.
LOCAL_GOV_SUFFIX_RE = re.compile(r"(특별자치도|특별자치시|광역시|특별시|도)$")


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
    tags = {t.strip() for t in notice.get("hashtags", "").split(",")} & REGION_CODES

    if tags and tags != REGION_CODES:
        # scoped to one or more specific regions
        return TARGET_REGION in tags

    # untagged or tagged with every region => looks nationwide, but some
    # notices are actually issued by a single province (e.g. 충청남도,
    # 세종특별자치시) that just fills in every region hashtag. Only trust it
    # as nationwide if the issuing body isn't itself a province/metro gov.
    jrsd = notice.get("jrsdInsttNm", "")
    if TARGET_REGION in jrsd:
        return True
    return not LOCAL_GOV_SUFFIX_RE.search(jrsd)


def load_state() -> dict[str, str]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def save_state(state: dict[str, str]) -> None:
    cutoff = date.today() - timedelta(days=STATE_RETENTION_DAYS)
    pruned = {
        pid: seen for pid, seen in state.items()
        if datetime.strptime(seen, "%Y-%m-%d").date() >= cutoff
    }
    STATE_PATH.write_text(
        json.dumps(pruned, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def format_message(notices: list[dict]) -> list[str]:
    lines = [f"📋 기업마당 신규 지원사업 ({len(notices)}건)\n"]
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
