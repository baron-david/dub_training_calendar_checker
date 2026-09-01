#!/usr/bin/env python3
"""
check_appointments.py

Polls DubTraining's Acuity availability API directly (no browser needed)
and alerts you when a NEW date becomes available compared to the last run.

Usage:
    python check_appointments.py

Env vars:
    STATE_FILE          path to persist known-available dates (default: known_dates.json)
    NOTIFY_WEBHOOK_URL   optional Slack-style incoming webhook URL for push alerts
    MONTHS_AHEAD         how many months forward to check, including current (default: 3)
    GROUPME_BOT_ID      used to notify GroupMe channels
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import requests

OWNER = "ad1bb86c"
APPOINTMENT_TYPE_ID = "84360440"
CALENDAR_ID = "any"
TIMEZONE = "America/Los_Angeles"
BASE_URL = "https://dubtraining.as.me/api/scheduling/v1/availability/month"

STATE_FILE = Path(os.environ.get("STATE_FILE", "known_dates.json"))
SLACK_WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL")
GROUPME_BOT_ID = os.environ.get("GROUPME_BOT_ID")
MONTHS_AHEAD = int(os.environ.get("MONTHS_AHEAD", "3"))

BOOKING_URL = "https://dubtraining.as.me/schedule/ad1bb86c/appointment/84360440/calendar/any"


def month_starts(n: int) -> list[str]:
    """Return the first-of-month date strings for this month + (n-1) more months."""
    today = datetime.now(timezone.utc)
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}-01")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def fetch_month_availability(month: str) -> dict[str, bool]:
    params = {
        "owner": OWNER,
        "appointmentTypeId": APPOINTMENT_TYPE_ID,
        "calendarId": CALENDAR_ID,
        "timezone": TIMEZONE,
        "month": month,
    }
    resp = requests.get(BASE_URL, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def fetch_all_available_dates() -> set[str]:
    available = set()
    for month in month_starts(MONTHS_AHEAD):
        data = fetch_month_availability(month)
        available |= {date for date, is_open in data.items() if is_open}
    return available


def load_known_dates() -> set[str]:
    if STATE_FILE.exists():
        return set(json.loads(STATE_FILE.read_text()))
    return set()


def save_known_dates(dates: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(dates), indent=2))


def notify(new_dates: set[str]) -> None:
    message = (
        "New DubTraining appointment availability found:\n"
        + "\n".join(f"  - {d}" for d in sorted(new_dates))
        + f"\n\n{BOOKING_URL}"
    )
    print(message)

    if SLACK_WEBHOOK_URL:
        payload = json.dumps({"text": message}).encode()  # Slack-compatible; adjust for other targets
        req = urllib.request.Request(
            SLACK_WEBHOOK_URL, data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            print("Sent to Slack")
        except Exception as e:
            print(f"Warning: webhook notification failed: {e}", file=sys.stderr)

    if GROUPME_BOT_ID:
        payload = json.dumps({"bot_id": "3336b426282b474225c518d57c","text": "test text"}).encode()  # GroupMe-compatible; adjust for other targets
        req = urllib.request.Request(
            "https://api.groupme.com/v3/bots/post", data=payload, headers={"Content-Type": "application/json"}
        )
        print(payload)
        try:
            urllib.request.urlopen(req, timeout=10)
            print("Sent to GroupMe")
        except Exception as e:
            print(f"Warning: webhook notification failed: {e}", file=sys.stderr)


def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Checking availability...")

    try:
        current_dates = fetch_all_available_dates()
    except requests.RequestException as e:
        print(f"Error fetching availability: {e}", file=sys.stderr)
        sys.exit(1)

    known_dates = load_known_dates()
    new_dates = current_dates - known_dates

    # Dates that were available before but no longer are (informational only)
    closed_dates = known_dates - current_dates
    if closed_dates:
        print(f"No longer available: {sorted(closed_dates)}")

    if new_dates:
        notify(new_dates)
    else:
        print("No new dates since last check.")

    save_known_dates(current_dates)


if __name__ == "__main__":
    main()
