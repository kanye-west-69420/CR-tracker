import requests
import gspread
import os
from datetime import datetime

# --- CONFIGURATION ---
# These will be set by the GitHub Action using secrets
PLAYER_TAG = os.getenv("CR_PLAYER_TAG", "YOUR_PLAYER_TAG_HERE").replace('#', '%23')
BEARER_TOKEN = os.getenv("CR_BEARER_TOKEN", "YOUR_BEARER_TOKEN_HERE")

# --- GOOGLE SHEETS CONFIG ---
SERVICE_ACCOUNT_FILE = 'credentials.json' 
SHEET_NAME = 'Clash Royale History' # The exact name of your Google Sheet
WORKSHEET_NAME = 'Sheet1' # The name of the tab in your sheet

def fetch_and_process_battles():
    """Fetches battle data, filters for ladder matches, and extracts key stats."""
    api_url = f'https://api.clashroyale.com/v1/players/{PLAYER_TAG}/battlelog'
    headers = {'Authorization': f'Bearer {BEARER_TOKEN}'}
    print(f"[{datetime.now()}] Fetching data from API for tag {PLAYER_TAG}...")

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status() # Raises an error for bad responses (4xx or 5xx)
        battles = response.json()

        processed_data = []
        for battle in battles:
            if battle.get('gameMode', {}).get('name') == 'Ladder':
                player_info = battle['team'][0]
                trophy_change = player_info.get('trophyChange', 0)

                if trophy_change > 0: result = 'Win'
                elif trophy_change < 0: result = 'Loss'
                else: result = 'Draw'

                current_trophies = player_info.get('startingTrophies', 0) + trophy_change

                # This list will become a row in our sheet
                battle_record = [battle['battleTime'], result, trophy_change, current_trophies]
                processed_data.append(battle_record)

        print(f"Found {len(processed_data)} ladder battles.")
        # Reverse the list so the oldest battles are inserted first
        processed_data.reverse()
        return processed_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return []

def save_data_to_gsheet(data):
    """Saves the processed data to a Google Sheet, avoiding duplicates."""
    if not data:
        print("No new data to save.")
        return

    print("Connecting to Google Sheets...")
    gc = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    sh = gc.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

    # Check if header exists and add it if it doesn't
    if not sh.get('A1'):
        sh.append_row(['battleTime', 'result', 'trophyChange', 'currentTrophies'])

    # Get all battle times already in the sheet to prevent duplicates
    existing_battle_times = set(sh.col_values(1))

    new_rows = []
    for row in data:
        battle_time = row[0] # The battleTime is the first item in our list
        if battle_time not in existing_battle_times:
            new_rows.append(row)

    if new_rows:
        sh.append_rows(new_rows)
        print(f"Appended {len(new_rows)} new rows to Google Sheet.")
    else:
        print("No unique new battles to add.")

if __name__ == "__main__":
    if not all([PLAYER_TAG, BEARER_TOKEN]):
        print("Error: CR_PLAYER_TAG or CR_BEARER_TOKEN environment variables not set.")
    else:
        battle_data = fetch_and_process_battles()
        save_data_to_gsheet(battle_data)
        print("--- Script finished ---")
