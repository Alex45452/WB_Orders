from telethon import TelegramClient, events, sync
import settings
import handlers

def tg_client_start():
    client = TelegramClient('session_name', settings.api_id, settings.api_hash)
    client.start()
    return client

def main():
    client = tg_client_start()
    @client.on(events.NewMessage())
    async def bot_msg_handler(event):
        ...



if __name__ == "__main__":
    main()