import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantsAdmins
import tkinter as tk
import json
from datetime import datetime, timedelta
import os

BOT_TOKEN = '6693338309:AAHH0uz5adYG2Jnxz7aq2TJdZ7YSgC5WIZ0'
API_ID = 20653175
API_HASH = 'a2b40a6be20565a5f064972c35222cf3'
file_path = "inactive_users.txt"

# Inicjalizacja klienta
client = TelegramClient('anon', API_ID, API_HASH).start(bot_token=BOT_TOKEN)


async def is_user_admin(user_id, chat_id):
    """Sprawdza, czy dany użytkownik jest administratorem w podanej grupie."""
    admin_list = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
    return any(admin.id == user_id for admin in admin_list)


async def get_admins(chat_id):
    """Zwraca listę ID administratorów w podanej grupie."""
    admin_list = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
    return [admin.id for admin in admin_list]


@client.on(events.NewMessage(incoming=True))
async def record_activity(event):
    # Kontynuuj tylko, jeśli wiadomość zawiera multimedia i nie jest odpowiedzią
    if not event.message.is_reply and event.media:
        user_id = event.sender_id
        username = event.sender.username or f"user{user_id}"

        # Load the activity data from the file if it exists, otherwise create an empty dictionary
        if os.path.exists('activity_data.json'):
            with open('activity_data.json', 'r') as file:
                try:
                    data = json.load(file)
                except json.JSONDecodeError:
                    data = {}
        else:
            data = {}

        # Update the activity data with the user's ID and last active time
        data[str(user_id)] = {
            "username": username,
            "last_active": str(datetime.now()),
            "user_id": user_id
        }

        # Write the updated data back to the file
        try:
            with open('activity_data.json', 'w') as file:
                json.dump(data, file, indent=4)
        except Exception as e:
            print(f"Error writing to activity_data.json: {e}")


@client.on(events.NewMessage(pattern=r'/showinactive (\d+) (h|d)'))
@client.on(events.NewMessage(pattern=r'/kickinactive (\d+) (h|d)'))
@client.on(events.NewMessage(pattern=r'/baninactive (\d+) (h|d)'))
async def process_inactive(event):
    if not await is_user_admin(event.sender_id, event.chat_id):
        await event.respond("Tylko administratorzy mogą używać tej komendy.")
        return

    days_or_hours = event.pattern_match.group(2)
    value = int(event.pattern_match.group(1))

    if days_or_hours == 'h':
        cutoff_date = datetime.now() - timedelta(hours=value)
    elif days_or_hours == 'd':  # Explicitly handling 'days'
        cutoff_date = datetime.now() - timedelta(days=value)
    else:
        await event.respond("Invalid time specifier. Use 'h' for hours or 'd' for days.")
        return

    # Load activity data
    if os.path.exists('activity_data.json'):
        with open('activity_data.json', 'r') as file:
            data = json.load(file)
    else:
        data = {}

    all_members = [member.id for member in await client.get_participants(event.chat_id) if
                   not await is_user_admin(member.id, event.chat_id)]
    active_members = [int(user_id) for user_id, user_data in data.items() if
                      datetime.fromisoformat(user_data["last_active"]) > cutoff_date]
    inactive_users = set(all_members) - set(active_members)

    if event.pattern_match.string.startswith("/showinactive"):
        msg_lines = [f"Użytkownik ID: {user_id}" for user_id in inactive_users]
        response_message = f"Użytkownicy nieaktywni od {value} {days_or_hours}:\n" + "\n".join(msg_lines) if msg_lines else "Brak nieaktywnych użytkowników."
        await event.respond(response_message)

    elif event.pattern_match.string.startswith("/kickinactive"):
        for user_id in inactive_users:
            try:
                await client.kick_participant(event.chat_id, user_id)
            except Exception as e:
                await event.respond(f"Nie mogę wyrzucić użytkownika ID {user_id}: {str(e)}")

    elif event.pattern_match.string.startswith("/baninactive"):
        for user_id in inactive_users:
            try:
                await client.edit_permissions(event.chat_id, user_id, view_messages=False)
            except Exception as e:
                await event.respond(f"Nie mogę zbanować użytkownika ID {user_id}: {str(e)}")


@client.on(events.NewMessage(pattern=r'/info'))
async def info_command(event):
    if not await is_user_admin(event.sender_id, event.chat_id):
        await event.respond("Tylko administratorzy mogą używać tej komendy.")
        return

    commands = {
        "/showinactive [liczba] [h/d]": "Pokazuje listę użytkowników nieaktywnych przez określoną liczbę godzin (h) lub dni (d).",
        "/kickinactive [liczba] [h/d]": "Wyrzuca użytkowników nieaktywnych przez określoną liczbę godzin (h) lub dni (d).",
        "/baninactive [liczba] [h/d]": "Banuje użytkowników nieaktywnych przez określoną liczbę godzin (h) lub dni (d).",
        "/info": "Pokazuje tę listę komend."
    }

    info_msg = "\n".join([f"{cmd}: {desc}" for cmd, desc in commands.items()])
    await event.respond(info_msg)


with client:
    client.run_until_disconnected()
