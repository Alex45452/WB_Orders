from telethon import TelegramClient, events, sync
import settings
from browser_handlers import order_handler
from requests_handlers import add_to_cart_handler
import asyncio

MAX_PERCENT = 60


client = TelegramClient('Acc_with_bot_access', settings.api_id, settings.api_hash,system_version="4.16.30-vxCUSTOM")


def get_product_from_call(msg):
    url = msg.media.webpage.display_url
    product_id = int(url[url.find("g/")+len("g/"):url.rfind('/')])
    return product_id

def get_percent_from_call(text):
    return float(text[text.find('(')+1:text.find(')')-1])


@client.on(events.NewMessage(incoming=True,from_users=[settings.TEST_BOT_ID]))
async def bot_msg_handler(event):
    
    print("NEW MESSAGE FUCKs")
    
    if get_percent_from_call(event.message.message) > MAX_PERCENT:
        return

    await client.send_message(settings.TEST_CHANNEL_ID,event.message)
    # product_id = get_product_from_call(event.message)
    # if add_to_cart_handler(product_id):
    #     order_handler() 

# async def main():
    
# client.add_event_handler(bot_msg_handler, events.NewMessage(incoming=True,from_users=[settings.TEST_BOT_ID]))

if __name__ == "__main__":
    client.start()
    client.run_until_disconnected()
    client.session.save()