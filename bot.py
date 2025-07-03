import os
import asyncio
import firebase_admin
from firebase_admin import credentials, firestore
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError

# --- Configuration ---
# IMPORTANT: Replace these with your actual credentials.
# It's highly recommended to use environment variables for security.
TELEGRAM_BOT_TOKEN = "7701117489:AAHLW5qaQ_oIzXXbiYdqXvRCIbM26M_WWJw"
TELEGRAM_CHAT_ID = "6412992293" # This is where the bot will send notifications.

# --- Firebase Setup ---
# Download your Firebase service account key JSON file and place it in the same directory as this script.
# Rename the file to "serviceAccountKey.json" or update the path below.
SERVICE_ACCOUNT_KEY_PATH = "serviceAccountKey.json"

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Successfully connected to Firebase.")
except Exception as e:
    print(f"Error connecting to Firebase: {e}")
    print("Please make sure the serviceAccountKey.json file is in the correct directory and is valid.")
    exit()

# --- Telegram Bot Setup ---
# Initialize the bot once, globally.
bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def send_new_student_notification(student_data):
    """Formats and sends a message for a new student registration."""
    name = student_data.get('name', 'N/A')
    phone = student_data.get('phone', 'N/A')
    email = student_data.get('email', 'N/A')
    telegram = student_data.get('telegramUsername', 'N/A')
    source = student_data.get('source', 'N/A')
    partner_id = student_data.get('partnerId', 'N/A')

    message = (
        f"🎉 *New Student Registration!* 🎉\n\n"
        f"👤 *Name:* {name}\n"
        f"📞 *Phone:* `{phone}`\n"
        f"📧 *Email:* {email}\n"
        f"✈️ *Telegram:* {telegram}\n"
        f"🤝 *Partner ID:* `{partner_id}`\n"
        f"🔍 *Source:* {source}\n\n"
        f"Please contact the student to follow up."
    )

    try:
        await bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN
        )
        print(f"Successfully sent notification for {name}.")
    except TelegramError as e:
        # More specific error handling for Telegram issues
        print(f"Error sending Telegram notification for {name}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending notification for {name}: {e}")

async def main():
    """Main async function to set up listener and run the event loop."""
    
    # Get the current running event loop.
    loop = asyncio.get_running_loop()
    
    # This event will keep the program running until we stop it (e.g., with Ctrl+C)
    stop_event = asyncio.Event()

    # Define the callback function for Firestore.
    # It will run in a background thread managed by Firebase.
    def on_snapshot(col_snapshot, changes, read_time):
        for change in changes:
            if change.type.name == 'ADDED':
                new_student_data = change.document.to_dict()
                print(f"New student detected: {new_student_data.get('name')}")
                
                # This is the key change:
                # Safely schedule the async coroutine to run on the main event loop
                # from this background thread.
                asyncio.run_coroutine_threadsafe(
                    send_new_student_notification(new_student_data), 
                    loop
                )

    # Set up the Firestore listener
    students_collection_ref = db.collection('students')
    collection_watch = students_collection_ref.on_snapshot(on_snapshot)

    print("Bot is running and listening for new student registrations...")
    print("Press Ctrl+C to stop.")
    
    try:
        # Wait on the event. This keeps the main function and its event loop alive.
        await stop_event.wait()
    except KeyboardInterrupt:
        print("\nStopping bot...")
    finally:
        # Clean up the listener when the bot is stopped.
        collection_watch.unsubscribe()
        print("Firestore listener stopped. Bot has shut down.")

if __name__ == '__main__':
    try:
        # This starts the single, long-running event loop.
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")