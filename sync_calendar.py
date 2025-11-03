
import datetime
import os.path
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_google_calendar_service():
    """Shows basic usage of the Google Calendar API.
    Prints the start and name of the next 10 events on the user's calendar.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    
    return build("calendar", "v3", credentials=creds)

import requests

def get_dooray_events(calendar_ids):
    """Fetches events for the current and next month in separate calls, then combines and filters them."""
    print("Fetching events for current and next month...")
    
    try:
        with open("dooray_api_key.txt", "r") as f:
            api_token = f.read().strip()
    except FileNotFoundError:
        print("Error: dooray_api_key.txt not found.")
        return []

    headers = {"Authorization": f"dooray-api {api_token}"}
    all_events = []
    
    # Loop to fetch for current month and next month
    for i in range(2): # 0 for current month, 1 for next month
        today = datetime.date.today()
        target_month_date = today.replace(day=1)
        
        # Logic to move to the target month
        year = today.year + (today.month + i -1) // 12
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

    # Filter the combined events by the provided calendar IDs
    print(f"\nFetched {len(all_events)} total events. Now filtering.")
    filtered_events = [
        event for event in all_events 
        if event.get("calendar", {}).get("id") in calendar_ids
    ]
    
    print(f"Found {len(filtered_events)} events in the target calendars: {calendar_ids}")
    return filtered_events

SYNC_STATE_FILE = "sync_state.json"

def load_sync_state():
    """Loads the sync state from a JSON file."""
    if not os.path.exists(SYNC_STATE_FILE):
        return {}
    try:
        with open(SYNC_STATE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_sync_state(state):
    """Saves the sync state to a JSON file."""
    with open(SYNC_STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

def synchronize_events(service, dooray_events):
    """Synchronizes Dooray events to Google Calendar, handling adds, updates, and deletes."""
    print(f"\nStarting true synchronization...")
    sync_state = load_sync_state()
    
    source_event_map = {event['id']: event for event in dooray_events}
    source_event_ids = set(source_event_map.keys())
    synced_dooray_ids = set(sync_state.keys())

    # Identify events to add, update, and delete
    events_to_add = source_event_ids - synced_dooray_ids
    events_to_delete = synced_dooray_ids - source_event_ids
    potential_updates = source_event_ids.intersection(synced_dooray_ids)

    # --- Process Deletions ---
    if events_to_delete:
        print(f"\nFound {len(events_to_delete)} events to DELETE from Google Calendar.")
        for dooray_id in events_to_delete:
            google_id = sync_state.pop(dooray_id) # Remove from state
            try:
                service.events().delete(calendarId='primary', eventId=google_id).execute()
                print(f"- Event DELETED: Dooray ID {dooray_id}")
            except HttpError as e:
                if e.resp.status == 404:
                    print(f"- Event already deleted on Google Calendar (Dooray ID: {dooray_id})")
                else:
                    print(f"- Error deleting event (Dooray ID: {dooray_id}): {e}")
                    sync_state[dooray_id] = google_id # Re-add to state if delete failed

    # --- Process Additions ---
    if events_to_add:
        print(f"\nFound {len(events_to_add)} new events to ADD to Google Calendar.")
        for dooray_id in events_to_add:
            event = source_event_map[dooray_id]
            subject = event.get("subject", "(No Title)")
            is_whole_day = event.get("wholeDayFlag", False)

            if is_whole_day:
                start = {"date": event.get("startedAt", "").split("+")[0]}
                end = {"date": event.get("endedAt", "").split("+")[0]}
            else:
                start = {"dateTime": event.get("startedAt"), "timeZone": "Asia/Seoul"}
                end = {"dateTime": event.get("endedAt"), "timeZone": "Asia/Seoul"}

            google_event_body = {
                "summary": subject,
                "location": event.get("location", ""),
                "start": start,
                "end": end,
                "description": f"Synced from Dooray. Event ID: {dooray_id}",
            }
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

            # --- Build the expected Google event structure from the Dooray event --- 
            expected_summary = dooray_event.get("subject", "(No Title)")
            if dooray_event.get("wholeDayFlag", False):
                expected_start = {"date": dooray_event.get("startedAt", "").split("+")[0]}
                expected_end = {"date": dooray_event.get("endedAt", "").split("+")[0]}
            else:
                expected_start = {"dateTime": dooray_event.get("startedAt"), "timeZone": "Asia/Seoul"}
                expected_end = {"dateTime": dooray_event.get("endedAt"), "timeZone": "Asia/Seoul"}

            # --- Compare actual vs expected --- 
            is_changed = False
            if google_event.get('summary') != expected_summary:
                is_changed = True
            if google_event.get('start') != expected_start:
                is_changed = True
            if google_event.get('end') != expected_end:
                is_changed = True

            if is_changed:
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
                print(f"- Event is up-to-date: {expected_summary}")

    save_sync_state(sync_state)
    print("\nState file updated.")

def main():
    """
    Main function to orchestrate the calendar synchronization.
    """
    # --- User Configuration ---
    TARGET_CALENDAR_IDS = ["3771874802837352562"] # 김승종 캘린더 ID
    # ------------------------

    print("Starting calendar synchronization...")
    
    service = None
    try:
        service = get_google_calendar_service()
        print("Successfully authenticated with Google Calendar.")
    except FileNotFoundError:
        print("Error: credentials.json not found. Please download it from Google Cloud Console.")
        return
    except Exception as e:
        print(f"An unexpected error occurred during Google authentication: {e}")
        return

    dooray_events = get_dooray_events(TARGET_CALENDAR_IDS)

    if service:
        synchronize_events(service, dooray_events)

    print("\nSynchronization process finished.")


if __name__ == "__main__":
    main()
