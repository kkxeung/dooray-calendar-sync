import datetime
import os.path
import json
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import requests

# --- Configuration Files ---
SYNC_STATE_FILE = "sync_state.json"
CONFIG_FILE = "config.json"

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# --- Helper Functions for Config and State ---
def load_json_file(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_json_file(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_config():
    return load_json_file(CONFIG_FILE)

def save_config(config):
    save_json_file(CONFIG_FILE, config)

def load_sync_state():
    return load_json_file(SYNC_STATE_FILE)

def save_sync_state(state):
    save_json_file(SYNC_STATE_FILE, state)

# --- Google Calendar API Functions ---
def get_google_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)

# --- Dooray API Functions ---
def get_dooray_api_token():
    try:
        with open("dooray_api_key.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print("Error: dooray_api_key.txt not found. Please create it and put your Dooray API token inside.")
        sys.exit(1)

def list_dooray_calendars():
    print("Fetching list of Dooray calendars...")
    api_token = get_dooray_api_token()
    headers = {"Authorization": f"dooray-api {api_token}"}

    try:
        response = requests.get("https://api.dooray.com/calendar/v1/calendars", headers=headers)
        response.raise_for_status()
        data = response.json()
        calendars = data.get("result", [])
        return calendars
    except requests.exceptions.RequestException as e:
        print(f"An error occurred while fetching Dooray calendars: {e}")
        sys.exit(1)
    except json.JSONDecodeError:
        print("Failed to decode JSON from Dooray API response when listing calendars.")
        sys.exit(1)

def get_dooray_events(target_calendar_id):
    print(f"Fetching events for calendar ID: {target_calendar_id}")
    api_token = get_dooray_api_token()
    headers = {"Authorization": f"dooray-api {api_token}"}
    all_events = []
    
    # Loop to fetch events from last month, current month, and next month
    for i in range(-1, 2): # -1 for last month, 0 for current, 1 for next
        today = datetime.date.today()
        
        # Calculate the target month and year
        # This logic correctly handles past (i < 0) and future (i > 0) months
        year = today.year + (today.month + i - 1) // 12
        month = (today.month + i - 1) % 12 + 1
        target_month_date = datetime.date(year, month, 1)

        # Find the last day of that month
        next_month_year = target_month_date.year + (target_month_date.month) // 12
        next_month_month = (target_month_date.month % 12) + 1
        first_day_of_next_month = datetime.date(next_month_year, next_month_month, 1)
        last_day_of_target_month = first_day_of_next_month - datetime.timedelta(days=1)

        time_min = target_month_date.isoformat()
        time_max = last_day_of_target_month.isoformat()

        print(f"- Querying for range: {time_min} to {time_max}")

        params = {
            "timeMin": f"{time_min}T00:00:00+09:00",
            "timeMax": f"{time_max}T23:59:59+09:00",
            "calendars": target_calendar_id # Use the correct query parameter
        }

        try:
            url = "https://api.dooray.com/calendar/v1/calendars/*/events"
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            monthly_events = data.get("result", [])
            print(f"  - Found {len(monthly_events)} events in this range.")
            all_events.extend(monthly_events)

        except requests.exceptions.RequestException as e:
            print(f"  - An error occurred while fetching Dooray events for this range: {e}")
        except json.JSONDecodeError:
            print("  - Failed to decode JSON from Dooray API response for this range.")

    print(f"Successfully fetched a total of {len(all_events)} events for calendar ID {target_calendar_id}.")
    return all_events

# --- User Interaction Functions ---
def get_user_selected_calendar_id(dry_run=False):
    config = load_config()
    selected_id = config.get("selected_calendar_id")

    if selected_id:
        print(f"Using previously selected calendar ID: {selected_id}")
        return selected_id

    calendars = list_dooray_calendars()
    if not calendars:
        print("No Dooray calendars found. Please check your API token and permissions.")
        sys.exit(1)

    print("\n--- Available Dooray Calendars ---")
    for i, cal in enumerate(calendars):
        print(f"{i+1}. Name: {cal.get('name', 'Unknown')}, ID: {cal.get('id', 'Unknown')}")
    print("----------------------------------")

    while True:
        try:
            choice = input("Please enter the number of the calendar you want to sync: ")
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(calendars):
                selected_calendar = calendars[choice_idx]
                selected_id = selected_calendar['id']
                print(f"Selected calendar: {selected_calendar.get('name')} (ID: {selected_id})")
                
                if not dry_run: # Only save if not in dry run mode
                    config["selected_calendar_id"] = selected_id
                    save_config(config)
                    print("Calendar selection saved to config.json.")
                else:
                    print("[DRY RUN] Calendar selection would have been saved to config.json.")
                return selected_id
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

# --- Synchronization Logic ---
def synchronize_events(service, dooray_events, target_calendar_id, dry_run=False):
    print(f"\nStarting synchronization for calendar ID: {target_calendar_id}...")
    sync_state = load_sync_state()
    
    source_event_map = {{event['id']: event for event in dooray_events}}
    source_event_ids = set(source_event_map.keys())
    synced_dooray_ids = set(sync_state.keys())

    # Identify events to add, update, and delete
    events_to_add = source_event_ids - synced_dooray_ids
    events_to_delete = synced_dooray_ids - source_event_ids
    potential_updates = source_event_ids.intersection(synced_dooray_ids)

    # --- Process Deletions ---
    if events_to_delete:
        print(f"\nFound {len(events_to_delete)} events to check for deletion from Google Calendar.")
        
        for dooray_id in list(events_to_delete):
            google_id = sync_state.get(dooray_id)
            if not google_id: continue

            try:
                google_event = service.events().get(calendarId='primary', eventId=google_id).execute()
                end_time_str = google_event.get('end', {}).get('date') or google_event.get('end', {}).get('dateTime')
                event_end_date = datetime.datetime.strptime(end_time_str[:10], '%Y-%m-%d').date()

                if event_end_date < datetime.date.today():
                    print(f"- Preserving history: '{google_event.get('summary')}' (ended {event_end_date})")
                    continue

            except HttpError as e:
                if e.resp.status == 404:
                    if not dry_run:
                        sync_state.pop(dooray_id, None)
                    print(f"- State cleaned for event already deleted on Google Calendar (Dooray ID: {dooray_id})")
                    continue
                else:
                    print(f"- Could not verify event {dooray_id} for deletion, skipping: {e}")
                    continue
            except (ValueError, TypeError):
                print(f"- Could not parse date for event {dooray_id}, skipping deletion.")
                continue

            if dry_run:
                print(f"[DRY RUN] Would DELETE event: '{google_event.get('summary', f'Dooray ID {dooray_id}')}'")
                continue

            try:
                sync_state.pop(dooray_id)
                service.events().delete(calendarId='primary', eventId=google_id).execute()
                print(f"- Event DELETED: Dooray ID {dooray_id}")
            except HttpError as e:
                if e.resp.status != 404:
                    print(f"- Error during final deletion of event (Dooray ID: {dooray_id}): {e}")
                    sync_state[dooray_id] = google_id

    # --- Process Additions ---
    if events_to_add:
        print(f"\nFound {len(events_to_add)} new events to ADD to Google Calendar.")
        for dooray_id in events_to_add:
            event = source_event_map[dooray_id]
            subject = event.get("subject", "(No Title)")
            is_whole_day = event.get("wholeDayFlag", False)

            if is_whole_day:
                start = {{"date": event.get("startedAt", "").split("+")[0]}}
                end = {{"date": event.get("endedAt", "").split("+")[0]}}
            else:
                start = {{"dateTime": event.get("startedAt"), "timeZone": "Asia/Seoul"}}
                end = {{"dateTime": event.get("endedAt"), "timeZone": "Asia/Seoul"}}

            google_event_body = {
                "summary": subject,
                "location": event.get("location", ""),
                "start": start,
                "end": end,
                "description": f"Synced from Dooray. Event ID: {dooray_id}",
            }
            
            if dry_run:
                print(f"[DRY RUN] Would CREATE event: '{subject}'")
                continue

            try:
                created_event = service.events().insert(calendarId="primary", body=google_event_body).execute()
                google_id = created_event.get('id')
                print(f"- Event CREATED: {subject} -> {created_event.get('htmlLink')}")
                sync_state[dooray_id] = google_id
            except HttpError as e:
                print(f"- Error creating event '{subject}': {e}")

    # --- Process Updates ---
    if potential_updates:
        print(f"\nChecking {len(potential_updates)} existing events for updates...")
        for dooray_id in potential_updates:
            dooray_event = source_event_map[dooray_id]
            google_id = sync_state[dooray_id]

            try:
                google_event = service.events().get(calendarId='primary', eventId=google_id).execute()
            except HttpError as e:
                print(f"- Could not fetch Google event {google_id} for comparison: {e}")
                continue

            expected_summary = dooray_event.get("subject", "(No Title)")
            if dooray_event.get("wholeDayFlag", False):
                expected_start = {{"date": dooray_event.get("startedAt", "").split("+")[0]}}
                expected_end = {{"date": dooray_event.get("endedAt", "").split("+")[0]}}
            else:
                expected_start = {{"dateTime": dooray_event.get("startedAt"), "timeZone": "Asia/Seoul"}}
                expected_end = {{"dateTime": dooray_event.get("endedAt"), "timeZone": "Asia/Seoul"}}

            is_changed = (google_event.get('summary') != expected_summary or
                          google_event.get('start') != expected_start or
                          google_event.get('end') != expected_end)

            if is_changed:
                if dry_run:
                    print(f"[DRY RUN] Would UPDATE event: '{expected_summary}'")
                    continue
                
                new_body = google_event.copy()
                new_body['summary'] = expected_summary
                new_body['start'] = expected_start
                new_body['end'] = expected_end
                try:
                    updated_event = service.events().update(calendarId='primary', eventId=google_id, body=new_body).execute()
                    print(f"- Event UPDATED: {updated_event.get('summary')}")
                except HttpError as e:
                    print(f"- Error updating event {expected_summary}: {e}")
            else:
                # This is a read-only check, so no dry-run difference
                print(f"- Event is up-to-date: {expected_summary}")

    if not dry_run:
        save_sync_state(sync_state)
        print("\nState file updated.")
    else:
        print("\n[DRY RUN] State file was NOT updated.")

# --- Main Execution ---
def main():
    print("Starting calendar synchronization...")
    
    dry_run_mode = '--dry-run' in sys.argv # Define dry_run_mode early

    # 1. Get user selected calendar ID
    target_calendar_id = get_user_selected_calendar_id(dry_run=dry_run_mode)
    if not target_calendar_id:
        print("No calendar selected. Exiting.")
        sys.exit(0)

    # 2. Authenticate with Google Calendar
    service = None
    try:
        service = get_google_calendar_service()
        print("Successfully authenticated with Google Calendar.")
    except FileNotFoundError:
        print("Error: credentials.json not found. Please download it from Google Cloud Console.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred during Google authentication: {e}")
        sys.exit(1)

    # 3. Fetch events from Dooray
    dooray_events = get_dooray_events(target_calendar_id)

    # 4. Synchronize events to Google Calendar
    if service:
        dry_run_mode = '--dry-run' in sys.argv
        if dry_run_mode:
            print("\n--- RUNNING IN DRY-RUN MODE: No changes will be made. ---")
        synchronize_events(service, dooray_events, target_calendar_id, dry_run=dry_run_mode)

    print("\nSynchronization process finished.")


if __name__ == "__main__":
    main()