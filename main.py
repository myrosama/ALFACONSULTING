# main.py

import os
import json
import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from keep_alive import keep_alive # Import the keep_alive function

# --- Configuration from Secrets ---
# Load credentials securely from Replit's environment variables (Secrets)
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
FIREBASE_CREDS_JSON_STR = os.environ.get('FIREBASE_CREDS_JSON')

if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, FIREBASE_CREDS_JSON_STR]):
    print("FATAL ERROR: One or more environment variables are not set.")
    print("Please check your Secrets in the Replit sidebar.")
    exit()

# --- Firebase Setup ---
# Initialize Firebase from the JSON string stored in Secrets
try:
    firebase_creds_dict = json.loads(FIREBASE_CREDS_JSON_STR)
    cred = credentials.Certificate(firebase_creds_dict)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Successfully connected to Firebase.")
except Exception as e:
    print(f"Error connecting to Firebase: {e}")
    print("Please ensure the FIREBASE_CREDS_JSON secret is a valid JSON string.")
    exit()

# --- Telegram Bot Setup ---
bot = Bot(token=TELEGRAM_BOT_TOKEN)


async def send_new_student_notification(student_data):
    """Formats and sends a message for a new student registration."""
    name = student_data.get('name', 'N/A')
    phone = student_data.get('phone', 'N/A')
    email = student_data.get('email', 'N/A')
    telegram = student_data.get('telegramUsername', 'N/A')
    source = student_data.get('source', 'N/A')
    partner_id = student_data.get('partnerId', 'N/A')

    message = (f"🎉 *New Student Registration!* 🎉\n\n"
               f"👤 *Name:* {name}\n"
               f"📞 *Phone:* `{phone}`\n"
               f"📧 *Email:* {email}\n"
               f"✈️ *Telegram:* {telegram}\n"
               f"🤝 *Partner ID:* `{partner_id}`\n"
               f"🔍 *Source:* {source}\n\n"
               f"Please contact the student to follow up.")

    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID,
                               text=message,
                               parse_mode=ParseMode.MARKDOWN)
        print(f"Successfully sent notification for {name}.")
    except TelegramError as e:
        print(f"Error sending Telegram notification for {name}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending notification for {name}: {e}")


async def main():
    """Main async function to set up listener and run the event loop."""
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                new_student_data = change.document.to_dict()
                print(f"New student detected: {new_student_data.get('name')}")
                asyncio.run_coroutine_threadsafe(
                    send_new_student_notification(new_student_data), loop)

    students_collection_ref = db.collection('students')
    collection_watch = students_collection_ref.on_snapshot(on_snapshot)

    print("Bot is running and listening for new student registrations...")
    print("Press Ctrl+C in console to stop (if running locally).")

    try:
        await stop_event.wait()
    except KeyboardInterrupt:
        print("\nStopping bot...")
    finally:
        collection_watch.unsubscribe()
        print("Firestore listener stopped. Bot has shut down.")


if __name__ == '__main__':
    # Start the web server to keep the bot alive
    keep_alive()
    print("Keep-alive server is running.")

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")
