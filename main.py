from telethon import TelegramClient, events, sync
import settings
from browser_handlers import order_handler
from requests_handlers import add_to_cart_handler


def get_product_from_call(msg):
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
        product_id = get_product_from_call(event)
        if add_to_cart_handler(product_id):
            order_handler() 


if __name__ == "__main__":
    main()