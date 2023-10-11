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
    for admin in admin_list:
        if admin.id == user_id:
            return True
    return False


@client.on(events.NewMessage(pattern='/start'))
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


@client.on(events.NewMessage(pattern='/show (\d+)'))
async def show_inactive(event):
    # Sprawdzanie, czy użytkownik jest administratorem
    if not await is_user_admin(event.sender_id, event.chat_id):
        await event.respond("Tylko administratorzy mogą używać tej komendy.")
        return

    days = int(event.pattern_match.group(1))
    cutoff_date = datetime.now() - timedelta(days=days)

    with open('activity_data.json', 'r') as file:
        data = json.load(file)

    all_members = [(member.username, member.id) for member in await client.get_participants(event.chat_id)]
    active_members = [(user_data["username"], int(user_id)) for user_id, user_data in data.items() if
                      datetime.fromisoformat(user_data["last_active"]) > cutoff_date]
    inactive_users = set(all_members) - set(active_members)

    msg_lines = [f"{username} (ID: {user_id})" for username, user_id in inactive_users if username]

    if len(msg_lines) > 50:
        # Jeśli jest więcej niż 50 nieaktywnych użytkowników, zapisz ich do pliku tekstowego
        with open(file_path, 'w') as file:
            file.write("\n".join(msg_lines))

        # Wyślij plik tekstowy prywatnie do użytkownika, który wpisał komendę
        await client.send_file(event.sender_id, file_path, caption=f"Użytkownicy nieaktywni od {days} dni:")
        await event.respond("Wysłałem Ci listę nieaktywnych użytkowników prywatnie.")
    else:
        # Jeśli jest mniej lub równo 50 nieaktywnych użytkowników, kontynuuj wysyłanie wiadomości w grupie
        msg = f"Użytkownicy nieaktywni od {days} dni:\n" + "\n".join(msg_lines)
        await event.respond(msg)


with client:
    client.run_until_disconnected()