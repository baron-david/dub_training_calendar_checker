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
#APPOINTMENT_TYPE_ID = "84389518"
#CALENDAR_ID = "any"
APPOINTMENT_TYPE_ID = "84360440"
CALENDAR_ID = "12864420"
TIMEZONE = "America/Los_Angeles"
BASE_URL = "https://dubtraining.as.me/api/scheduling/v1/availability/month"
TIMES_URL = "https://dubtraining.as.me/api/scheduling/v1/availability/times"

STATE_FILE = Path(os.environ.get("STATE_FILE", "known_dates_test.json"))
SLACK_WEBHOOK_URL = os.environ.get("NOTIFY_WEBHOOK_URL")
GROUPME_BOT_ID = os.environ.get("GROUPME_BOT_ID")
MONTHS_AHEAD = int(os.environ.get("MONTHS_AHEAD", "3"))

BOOKING_URL = "<https://dubtraining.as.me/?|Book Here!>"


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


def fetch_times_for_date(day: str, calendar_id: str = CALENDAR_ID) -> list[dict]:
    """Return the list of available time slots for a single date (YYYY-MM-DD).
 
    The API responds with {"<date>": [{"time": "...", "slotsAvailable": N}, ...]},
    so this unwraps that down to just the list of slot dicts.
    """
    params = {
        "owner": OWNER,
        "appointmentTypeId": APPOINTMENT_TYPE_ID,
        "calendarId": calendar_id,
        "startDate": day,
        "timezone": TIMEZONE,
    }
    resp = requests.get(TIMES_URL, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    return data.get(day, [])
 
def fetch_times_for_dates(days: set[str], calendar_id: str = CALENDAR_ID) -> dict[str, list[dict]]:
    """Fetch time slots for each date in `days`. Returns {date: [slot_dicts]}."""
    results = {}
    for day in sorted(days):
        try:
            results[day] = fetch_times_for_date(day, calendar_id)
        except requests.RequestException as e:
            print(f"Warning: failed to fetch times for {day}: {e}", file=sys.stderr)
            results[day] = []
    return results
 
 
def format_slots(slots: list[dict]) -> str:
    """Turn a list of slot dicts into a human-readable 'h:mm AM/PM (xN)' string."""
    if not slots:
        return "no slots returned"
    formatted = []
    for s in slots:
        try:
            t = datetime.fromisoformat(s["time"]).strftime("%I:%M %p").lstrip("0")
            formatted.append(f"{t} (x{s.get('slotsAvailable', '?')})")
        except (KeyError, ValueError) as e:
            formatted.append(f"<unparseable slot: {s} ({e})>")
    return ", ".join(formatted)


def save_known_dates(dates: set[str]) -> None:
    STATE_FILE.write_text(json.dumps(sorted(dates)[-30:], indent=2))


def notify(new_dates: set[str], times_by_date: dict[str, list[dict]] | None = None) -> None:
    lines = ["New DubTraining appointment availability found:"]
    for d in sorted(new_dates):
        if times_by_date and d in times_by_date:
            lines.append(f"  - {d}: {format_slots(times_by_date[d])}")
        else:
            lines.append(f"  - {d}")
    lines.append("")
    lines.append(BOOKING_URL)
    message = "\n".join(lines)
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
        payload = json.dumps({"bot_id": GROUPME_BOT_ID,"text": message}).encode()  # GroupMe-compatible; adjust for other targets
        req = urllib.request.Request(
            "https://api.groupme.com/v3/bots/post", data=payload, headers={"Content-Type": "application/json"}
        )
        try:
            urllib.request.urlopen(req, timeout=10)
            print("Sent to GroupMe")
        except Exception as e:
            print(f"Warning: webhook notification failed: {e}", file=sys.stderr)


def main() -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Checking All availability...")

    try:
        current_dates = fetch_all_available_dates()
    except requests.RequestException as e:
        print(f"Error fetching availability: {e}", file=sys.stderr)
        sys.exit(1)

    current_dates = set() # test empty data
    known_dates = load_known_dates()
    new_dates = current_dates - known_dates
    all_dates = current_dates | known_dates

    # Dates that were available before but no longer are (informational only)
    closed_dates = known_dates - current_dates
    if closed_dates:
        print(f"No longer available: {sorted(closed_dates)}")

  


## test code here
  # Fetch specific open times for any newly available dates

    times_by_date = fetch_times_for_dates(current_dates)

    times_only = remove_slots_available(times_by_date)
    current_times = {
        slot['time']
        for slots in times_only.values()
        for slot in slots
    }
    save_known_dates(current_times)

    new_times = current_times - known_dates
    if new_times:
        new_dates_split = {ts.split('T')[0] for ts in new_times}
        notify(new_dates_split,times_by_date)



def remove_slots_available(data: dict) -> dict:
    """Strip 'slotsAvailable' from each slot dict, keeping only 'time'."""
    return {
        date: [{'time': slot['time']} for slot in slots]
        for date, slots in data.items()
    }




## end test code


if __name__ == "__main__":
    main()
