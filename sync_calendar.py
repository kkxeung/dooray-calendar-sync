import argparse
import datetime as dt
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/calendar"]
SYNC_STATE_FILE = "sync_state.json"
CONFIG_FILE = "config.json"


@dataclass
class AppConfig:
    dooray_calendar_ids: List[str]
    google_calendar_id: str = "primary"
    timezone: str = "Asia/Seoul"
    months_ahead: int = 2  # current month + (months_ahead-1)


def load_json_file(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return default


def save_json_file(path: str, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_config() -> AppConfig:
    raw = load_json_file(CONFIG_FILE, {})

    env_calendar_ids = os.getenv("DOORAY_CALENDAR_IDS", "").strip()
    if env_calendar_ids:
        calendar_ids = [x.strip() for x in env_calendar_ids.split(",") if x.strip()]
    else:
        calendar_ids = raw.get("dooray_calendar_ids", [])

    google_calendar_id = os.getenv("GOOGLE_CALENDAR_ID", raw.get("google_calendar_id", "primary"))
    timezone = os.getenv("TIMEZONE", raw.get("timezone", "Asia/Seoul"))
    months_ahead = int(os.getenv("SYNC_MONTHS_AHEAD", raw.get("months_ahead", 2)))

    if not calendar_ids:
        raise ValueError(
            "No Dooray calendar IDs configured. Set DOORAY_CALENDAR_IDS or config.json: dooray_calendar_ids"
        )

    return AppConfig(
        dooray_calendar_ids=calendar_ids,
        google_calendar_id=google_calendar_id,
        timezone=timezone,
        months_ahead=max(1, months_ahead),
    )


def get_google_calendar_service():
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def read_dooray_api_token() -> str:
    env_token = os.getenv("DOORAY_API_TOKEN", "").strip()
    if env_token:
        return env_token

    if os.path.exists("dooray_api_key.txt"):
        with open("dooray_api_key.txt", "r", encoding="utf-8") as f:
            token = f.read().strip()
            if token:
                return token

    raise FileNotFoundError("Dooray API token not found. Use DOORAY_API_TOKEN or dooray_api_key.txt")


def month_range(today: dt.date, month_offset: int) -> Tuple[str, str]:
    year = today.year + (today.month + month_offset - 1) // 12
    month = (today.month + month_offset - 1) % 12 + 1

    start = dt.date(year, month, 1)
    if month == 12:
        next_month = dt.date(year + 1, 1, 1)
    else:
        next_month = dt.date(year, month + 1, 1)
    end = next_month - dt.timedelta(days=1)

    return start.isoformat(), end.isoformat()


def get_dooray_events(config: AppConfig):
    token = read_dooray_api_token()
    headers = {"Authorization": f"dooray-api {token}"}

    all_events = []
    overall_min = None
    overall_max = None

    today = dt.date.today()
    for i in range(config.months_ahead):
        time_min, time_max = month_range(today, i)
        if overall_min is None:
            overall_min = time_min
        overall_max = time_max

        params = {
            "timeMin": f"{time_min}T00:00:00+09:00",
            "timeMax": f"{time_max}T23:59:59+09:00",
        }

        url = "https://api.dooray.com/calendar/v1/calendars/*/events"
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        all_events.extend(payload.get("result", []))

    filtered = [
        e for e in all_events if e.get("calendar", {}).get("id") in config.dooray_calendar_ids
    ]

    query_min = f"{overall_min}T00:00:00+09:00" if overall_min else None
    query_max = f"{overall_max}T23:59:59+09:00" if overall_max else None

    return filtered, query_min, query_max


def load_sync_state() -> Dict[str, str]:
    data = load_json_file(SYNC_STATE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_sync_state(state: Dict[str, str]):
    save_json_file(SYNC_STATE_FILE, state)


def parse_event_start(google_event: dict, timezone: str) -> dt.datetime | None:
    start = google_event.get("start", {})
    if "dateTime" in start:
        value = start["dateTime"].replace("Z", "+00:00")
        return dt.datetime.fromisoformat(value)
    if "date" in start:
        # all-day event date is interpreted as local midnight
        return dt.datetime.fromisoformat(f"{start['date']}T00:00:00+09:00")
    return None


def to_google_fields(dooray_event: dict, timezone: str) -> dict:
    is_whole_day = dooray_event.get("wholeDayFlag", False)
    if is_whole_day:
        start = {"date": dooray_event.get("startedAt", "").split("+")[0]}
        end = {"date": dooray_event.get("endedAt", "").split("+")[0]}
    else:
        start = {"dateTime": dooray_event.get("startedAt"), "timeZone": timezone}
        end = {"dateTime": dooray_event.get("endedAt"), "timeZone": timezone}

    return {
        "summary": dooray_event.get("subject", "(No Title)"),
        "location": dooray_event.get("location", ""),
        "start": start,
        "end": end,
        "description": f"Synced from Dooray. Event ID: {dooray_event.get('id')}",
        "reminders": {"useDefault": False, "overrides": []},
    }


def synchronize_events(service, dooray_events, time_min, time_max, config: AppConfig, dry_run: bool = False):
    print("Starting synchronization...")
    sync_state = load_sync_state()

    source_map = {e["id"]: e for e in dooray_events}
    source_ids = set(source_map.keys())
    synced_ids = set(sync_state.keys())

    to_add = source_ids - synced_ids
    to_delete_candidates = synced_ids - source_ids
    to_check_update = source_ids & synced_ids

    min_dt = dt.datetime.fromisoformat(time_min.replace("Z", "+00:00"))
    max_dt = dt.datetime.fromisoformat(time_max.replace("Z", "+00:00"))

    if to_delete_candidates:
        print(f"Delete check: {len(to_delete_candidates)}")
    for dooray_id in to_delete_candidates:
        google_id = sync_state[dooray_id]
        try:
            ge = service.events().get(calendarId=config.google_calendar_id, eventId=google_id).execute()
            st = parse_event_start(ge, config.timezone)
            if st is None:
                print(f"- skip delete (unknown start): {dooray_id}")
                continue

            if min_dt <= st <= max_dt:
                print(f"- delete: {ge.get('summary')} ({dooray_id})")
                if not dry_run:
                    service.events().delete(calendarId=config.google_calendar_id, eventId=google_id).execute()
                    sync_state.pop(dooray_id, None)
            else:
                print(f"- keep (outside window): {ge.get('summary')} ({dooray_id})")

        except HttpError as e:
            if e.resp.status in [404, 410]:
                sync_state.pop(dooray_id, None)
                print(f"- already deleted in Google, state cleanup: {dooray_id}")
            else:
                print(f"- delete-check error {dooray_id}: {e}")

    if to_add:
        print(f"Add: {len(to_add)}")
    for dooray_id in to_add:
        body = to_google_fields(source_map[dooray_id], config.timezone)
        print(f"- create: {body.get('summary')} ({dooray_id})")
        if not dry_run:
            created = service.events().insert(calendarId=config.google_calendar_id, body=body).execute()
            sync_state[dooray_id] = created.get("id")

    if to_check_update:
        print(f"Update check: {len(to_check_update)}")
    for dooray_id in to_check_update:
        expected = to_google_fields(source_map[dooray_id], config.timezone)
        google_id = sync_state[dooray_id]

        try:
            current = service.events().get(calendarId=config.google_calendar_id, eventId=google_id).execute()
        except HttpError as e:
            print(f"- update-check fetch failed {dooray_id}: {e}")
            continue

        changed = (
            current.get("summary") != expected.get("summary")
            or current.get("start") != expected.get("start")
            or current.get("end") != expected.get("end")
            or current.get("location", "") != expected.get("location", "")
        )

        if changed:
            print(f"- update: {expected.get('summary')} ({dooray_id})")
            if not dry_run:
                new_body = current.copy()
                new_body.update(expected)
                service.events().update(
                    calendarId=config.google_calendar_id,
                    eventId=google_id,
                    body=new_body,
                ).execute()

    if not dry_run:
        save_sync_state(sync_state)
    print("Synchronization finished." + (" (dry-run)" if dry_run else ""))


def parse_args():
    parser = argparse.ArgumentParser(description="Sync Dooray calendar events to Google Calendar")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing to Google/state")
    return parser.parse_args()


def main():
    args = parse_args()

    try:
        config = load_config()
    except ValueError as e:
        print(f"Config error: {e}")
        return

    print("Starting calendar synchronization...")
    try:
        service = get_google_calendar_service()
    except FileNotFoundError:
        print("Error: credentials.json not found.")
        return
    except Exception as e:
        print(f"Google auth error: {e}")
        return

    try:
        dooray_events, time_min, time_max = get_dooray_events(config)
    except Exception as e:
        print(f"Dooray fetch error: {e}")
        return

    synchronize_events(service, dooray_events, time_min, time_max, config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
