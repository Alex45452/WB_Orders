from telethon import TelegramClient, events, sync
from settings import api_id, api_hash, RTX_CUSTOMER_ID, CHANNEL_ID, BOT_ID, ACCOUNTS, created_orders
from browser_handlers import order_handler
import asyncio
import logging

MAX_PERCENT = 30
MIN_ORDER_PERCENT = 9
MIN_RATING = 4.5

logger = logging.getLogger(__name__)
logging.basicConfig(filename='wb.log', level=logging.INFO)

def exc_handler(loop,context):
    logger.error(context["message"])

try:
    asyncio.get_event_loop()
except:
    loop = asyncio.new_event_loop()
    loop.set_exception_handler(exc_handler)
    asyncio.set_event_loop(loop)
    

client = TelegramClient('Acc_with_bot_access', api_id, api_hash,system_version="4.16.30-vxCUSTOM")


def get_product_from_msg(msg):
    url = msg.media.webpage.display_url
    product_id = int(url[url.find("g/")+len("g/"):url.rfind('/')])
    return product_id

def get_percent_from_call(text):
    text = text[text.find("Выгода"):]
    return float(text[text.find('(')+1:text.find(')')-1])

def get_seller_rating_from_call(text):
    st = text.rfind('Рейтинг: ')+len("Рейтинг: ")
    return float(text[st:st+3])

def get_product_rating_from_call(text):
    st = text.find('Рейтинг: ')+len("Рейтинг: ")
    return float(text[st:st+3])

def check_no_customs_from_call(text):
    return text.find("ошлин") == -1  # check Пошлина

def check_call_conditions(event):
    cur_percent = get_percent_from_call(event.message.message)
    cur_seller_rating = get_seller_rating_from_call(event.message.message)
    cur_product_rating = get_product_rating_from_call(event.message.message)
    return (cur_percent > MAX_PERCENT or 
            cur_seller_rating < MIN_RATING or 
            0 != cur_product_rating < MIN_RATING or 
            not check_no_customs_from_call(event.message.message))

def get_msg_recipient(text):
    if text.find("RTX") != -1 or text.find("intel") != -1 or text.find("ryzen") != -1:
        return RTX_CUSTOMER_ID
    return CHANNEL_ID

async def msg_processing(event):
    if check_call_conditions(event):
        return 
    cur_recipient = get_msg_recipient(event.message.message)
    await client.send_message(cur_recipient,event.message)
    # if cur_percent > MIN_ORDER_PERCENT and cur_recipient != RTX_CUSTOMER_ID:
    #     product_id = get_product_from_msg(event.message)
    #     for acc_id in range(len(ACCOUNTS)-1,-1,-1):
    #         asyncio.create_task(order_handle_w_check(acc_id,product_id))     
    #         logger.info(f"task created for acc_id: {acc_id} for porduct_id: {product_id}")

async def order_handle_w_check(acc_id,product_id):         
    order_id = await order_handler(acc_id,product_id)
    if order_id:
        logger.info(f"order was created for acc_id: {0} order_id: {order_id}")
        created_orders[acc_id].append(order_id)
    else:
        logger.info(f"order was NOT created for acc_id: {0} order_id: {order_id}")


async def bot_msg_handler(event):
    logger.info("Got new message from bot")
    asyncio.create_task(msg_processing(event))
    

if __name__ == "__main__":
    client.start()
    client.add_event_handler(bot_msg_handler, events.NewMessage(incoming=True,from_users=[BOT_ID]))
    
    logger.info("Client started!")
    client.run_until_disconnected()
    logger.info("Client disconnected, closing")
    client.session.save()