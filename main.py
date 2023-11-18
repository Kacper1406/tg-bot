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


@client.on(events.NewMessage(pattern=r'/showinactive (\d+)(h|d)'))
@client.on(events.NewMessage(pattern=r'/kickinactive (\d+)(h|d)'))
@client.on(events.NewMessage(pattern=r'/baninactive (\d+)(h|d)'))
async def process_inactive(event):
    if not await is_user_admin(event.sender_id, event.chat_id):
        await event.respond("Tylko administratorzy mogą używać tej komendy.")
        return

    days_or_hours = event.pattern_match.group(2)
    value = int(event.pattern_match.group(1))

    if days_or_hours == 'h':
        cutoff_date = datetime.now() - timedelta(hours=value)
    else:  # 'd'
        cutoff_date = datetime.now() - timedelta(days=value)

    with open('activity_data.json', 'r') as file:
        data = json.load(file)

    all_members = [(member.username, member.id) for member in await client.get_participants(event.chat_id) if
                   not await is_user_admin(member.id, event.chat_id)]
    active_members = [(user_data["username"], int(user_id)) for user_id, user_data in data.items() if
                      datetime.fromisoformat(user_data["last_active"]) > cutoff_date]
    inactive_users = set(all_members) - set(active_members)

    if event.pattern_match.string.startswith("/showinactive"):
        msg_lines = [f"{username} (ID: {user_id})" for username, user_id in inactive_users if username]
        await event.respond(f"Użytkownicy nieaktywni od {value} {days_or_hours}:\n" + "\n".join(msg_lines))

    elif event.pattern_match.string.startswith("/kickinactive"):
        for _, user_id in inactive_users:
            try:
                await client.kick_participant(event.chat_id, user_id)
            except Exception as e:
                await event.respond(f"Nie mogę wyrzucić użytkownika o ID {user_id}: {str(e)}")

    elif event.pattern_match.string.startswith("/baninactive"):
        for _, user_id in inactive_users:
            try:
                await client.edit_permissions(event.chat_id, user_id, view_messages=False)
            except Exception as e:
                await event.respond(f"Nie mogę zbanować użytkownika o ID {user_id}: {str(e)}")


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
