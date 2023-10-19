from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantsAdmins
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
    return user_id in [admin.id for admin in admin_list]


async def get_admins(chat_id):
    """Zwraca listę ID administratorów w podanej grupie."""
    admin_list = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
    return [admin.id for admin in admin_list]


@client.on(events.NewMessage(pattern=r'/start'))
async def start(event):
    await event.respond('Bot został uruchomiony.')


@client.on(events.NewMessage(incoming=True))
async def record_activity(event):
    user_id = event.sender_id
    username = event.sender.username

    if event.media:  # Jeśli wiadomość zawiera multimedia
        # Wczytaj dane aktywności z pliku
        if os.path.exists('activity_data.json'):
            with open('activity_data.json', 'r') as file:
                data = json.load(file)
        else:
            data = {}

        # Zaktualizuj dane aktywności
        data[str(user_id)] = {"username": username, "last_active": str(datetime.now())}

        # Zapisz aktualizowane dane do pliku
        with open('activity_data.json', 'w') as file:
            json.dump(data, file)


@client.on(events.NewMessage(pattern=r'/showinactive (\d+) (h|d)|/kickinactive (\d+) (h|d)|/baninactive (\d+) (h|d)'))
async def process_inactive(event):
    # Sprawdzanie, czy użytkownik jest administratorem
    if not await is_user_admin(event.sender_id, event.chat_id):
        await event.respond("Tylko administratorzy mogą używać tej komendy.")
        return

    # Wspólna logika do przetwarzania czasu
    if event.pattern_match.string.startswith("/showinactive"):
        number = int(event.pattern_match.group(1))
        unit = event.pattern_match.group(2)
    elif event.pattern_match.string.startswith("/kickinactive"):
        number = int(event.pattern_match.group(3))
        unit = event.pattern_match.group(4)
    elif event.pattern_match.string.startswith("/baninactive"):
        number = int(event.pattern_match.group(5))
        unit = event.pattern_match.group(6)

    if unit == "h":
        cutoff_date = datetime.now() - timedelta(hours=number)
    else:  # d
        cutoff_date = datetime.now() - timedelta(days=number)

    admin_ids = await get_admins(event.chat_id)

    with open('activity_data.json', 'r') as file:
        data = json.load(file)

    all_members = [(member.username, member.id) for member in await client.get_participants(event.chat_id) if
                   member.id not in admin_ids]
    active_members = [(user_data["username"], int(user_id)) for user_id, user_data in data.items() if
                      datetime.fromisoformat(user_data["last_active"]) > cutoff_date and int(user_id) not in admin_ids]
    inactive_users = set(all_members) - set(active_members)

    if event.pattern_match.string.startswith("/showinactive"):
        msg_lines = [f"{username} (ID: {user_id})" for username, user_id in inactive_users if username]
        if len(msg_lines) > 50:
            with open(file_path, 'w') as file:
                file.write("\n".join(msg_lines))
            await client.send_file(event.sender_id, file_path, caption=f"Użytkownicy nieaktywni od {number}{unit}:")
            await event.respond("Wysłałem Ci listę nieaktywnych użytkowników prywatnie.")
        else:
            msg = f"Użytkownicy nieaktywni od {number}{unit}:\n" + "\n".join(msg_lines)
            await event.respond(msg)

    elif event.pattern_match.string.startswith("/kickinactive"):
        for _, user_id in inactive_users:
            try:
                await client.kick_participant(event.chat_id, user_id)
            except Exception as e:
                await event.respond(f"Nie mogłem wyrzucić użytkownika o ID {user_id}. Błąd: {e}")
        await event.respond(f"Wyrzuciłem użytkowników nieaktywnych od {number}{unit}.")

    elif event.pattern_match.string.startswith("/baninactive"):
        for _, user_id in inactive_users:
            try:
                await client.edit_permissions(event.chat_id, user_id, view_messages=False)
            except Exception as e:
                await event.respond(f"Nie mogłem zbanować użytkownika o ID {user_id}. Błąd: {e}")
        await event.respond(f"Zbanowałem użytkowników nieaktywnych od {number}{unit}.")


with client:
    client.run_until_disconnected()
