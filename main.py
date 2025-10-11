from telethon import TelegramClient, events, sync
import settings
from browser_handle import order_handler

def get_url_from_call(msg):
    pass

def add_to_cart(url):
    pass

def tg_client_start():
    client = TelegramClient('session_name', settings.api_id, settings.api_hash)
    client.start()
    return client

def main():
    client = tg_client_start()
    @client.on(events.NewMessage())
    async def bot_msg_handler(event):
        ...
        url = get_url_from_call(event)
        add_to_cart(url)
        order_handler()


if __name__ == "__main__":
    main()