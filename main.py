from telethon import TelegramClient, events, sync
from settings import api_id, api_hash, RTX_CUSTOMER_ID, CHANNEL_ID, BOT_ID, ACCOUNTS
from browser_handlers import order_handler
from requests_handlers import add_to_cart_handler
import asyncio

MAX_PERCENT = 20
MIN_ORDER_PERCENT = 10

# loop = asyncio.new_event_loop()
# asyncio.set_event_loop(loop)

client = TelegramClient('Acc_with_bot_access', api_id, api_hash,system_version="4.16.30-vxCUSTOM")


def get_product_from_call(msg):
    url = msg.media.webpage.display_url
    product_id = int(url[url.find("g/")+len("g/"):url.rfind('/')])
    return product_id

def get_percent_from_call(text):
    return float(text[text.rfind('(')+1:text.rfind(')')-1])

def get_msg_recipient(text):
    if text.find("RTX") != -1:
        return RTX_CUSTOMER_ID
    return CHANNEL_ID

async def bot_msg_handler(event):
    
    print("Got new message from bot")
    cur_percent = get_percent_from_call(event.message.message)
    if  cur_percent > MAX_PERCENT :
        return
    cur_recipient = get_msg_recipient(event.message.message)
    await client.send_message(cur_recipient,event.message)
    if cur_percent > MIN_ORDER_PERCENT and cur_recipient != RTX_CUSTOMER_ID:
        product_id = get_product_from_call(event.message)
        for acc_id in range(len(ACCOUNTS)-1,-1,-1):
            asyncio.create_task(order_handler(acc_id,product_id))     

if __name__ == "__main__":
    client.start()
    client.add_event_handler(bot_msg_handler, events.NewMessage(incoming=True,from_users=[BOT_ID]))
    print("Client started!")
    client.run_until_disconnected()
    print("Client disconnected, closing")
    client.session.save()