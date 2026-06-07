import json
import re
from datetime import datetime

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

from telegram import Bot

# =====================================
# CONFIG
# =====================================
import os
BOT_TOKEN = os.environ["BOT_TOKEN"]

BOT_TOKEN = "8691893238:AAFr89KUmemYRORBAcsGQDyPw4NQXzR-DUU"

SPREADSHEET_NAME = "Reel Links"

STATE_FILE = "state.json"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# =====================================
# GOOGLE AUTH
# =====================================

def get_google_client():
    creds = None

    try:
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )
    except Exception:
        pass

    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            creds = flow.run_local_server(port=0)

        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return gspread.authorize(creds)

# =====================================
# STATE
# =====================================

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {
            "last_update_id": 0
        }

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

# =====================================
# HELPERS
# =====================================

def extract_urls(text):
    return re.findall(
        r'https?://[^\s]+',
        text
    )

def get_next_serial(sheet):

    values = sheet.col_values(2)

    if len(values) <= 1:
        return 1

    try:
        return int(values[-1]) + 1

    except Exception:
        return len(values)

# =====================================
# MAIN
# =====================================

async def main():

    # Google Sheets
    gc = get_google_client()
    sheet = gc.open(SPREADSHEET_NAME).sheet1

    # State
    state = load_state()
    last_update_id = state["last_update_id"]

    # Telegram
    bot = Bot(BOT_TOKEN)

    updates = await bot.get_updates(
        offset=last_update_id + 1,
        timeout=0
    )

    if not updates:
        print("No new messages.")
        return

    total_links_saved = 0

    serial = get_next_serial(sheet)

    rows = []

    chat_ids = set()

    newest_update_id = last_update_id

    for update in updates:

        newest_update_id = max(
            newest_update_id,
            update.update_id
        )

        if not update.message:
            continue

        chat_ids.add(update.message.chat_id)

        text = update.message.text or ""

        urls = extract_urls(text)

        for url in urls:

            rows.append([
                datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                serial,
                url
            ])

            serial += 1
            total_links_saved += 1

    if rows:
        sheet.append_rows(rows)

    # Save checkpoint
    state["last_update_id"] = newest_update_id
    save_state(state)

    # Notify chats
    for chat_id in chat_ids:
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"Saved {total_links_saved} link(s)"
            )
        except Exception as e:
            print(
                f"Couldn't send confirmation to {chat_id}: {e}"
            )

    print(
        f"Done. Saved {total_links_saved} link(s)."
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())