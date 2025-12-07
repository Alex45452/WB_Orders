from playwright.async_api import async_playwright
from playwright._impl._errors import TimeoutError
from requests_handlers import add_to_cart_handler
from settings import ACCOUNTS, cur_address
import json
import time
import asyncio
import logging

MAIN_PAGE_URL = "https://wildberries.ru"
BASKET_URL = "https://wildberries.ru/lk/basket"
NOT_TESTING = True


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_acc_cookies(acc_id):
    cookies = [
        {
        "name": "wbx-validation-key",
        "value": ACCOUNTS[acc_id]["WBX_VALIDATION_KEY"],
        "domain": ".wildberries.ru",
        "path": "/",
        "httponly": True,
        "secure": True,
        "sameSite": "Lax",
        # "expires": datetime.datetime.fromisoformat(TIME).timestamp()
        }
    ]
    return cookies

def get_full_cookies_for_httpx(context):
    return context.cookies(urls=MAIN_PAGE_URL)

def get_acc_wbx_token(acc_id):
    wbx_token = {"token":ACCOUNTS[acc_id]["TOKEN"],"pvKey":None,"slideOff":None}
    return wbx_token

async def botcheck_handler(page,context):
    try:
        await page.wait_for_selector("div.support-title", timeout=2000)
        logger.info("got bot check 1")
    except:
        logger.info("Bot check wasnt occure 1")
        return True

    try:
        await page.wait_for_selector("div.support", timeout=2000)
        logger.info("Got bot check fatal")
        return False
    except:
        logger.info("Bot check fatal wasnt occure")


    try:
        await page.wait_for_selector("div.support-title", timeout=2000)
        logger.info("trying to avoid bot check 2")
        await context.clear_cookies()
        await page.reload()
        await context.add_cookies(get_acc_cookies(acc_id))
        await page.reload()
    except:
        logger.info("Bot check wasnt occure 2")


    try:
        await page.wait_for_selector("div.support-title", timeout=2000)
        await context.clear_cookies()
        await page.reload()
        await context.add_cookies(get_acc_cookies(acc_id))
        await page.reload()
        await page.wait_for_selector("div.support-title", timeout=2000)
        logger.error("BOTCHECK CANT BE PASSED CANCELLING")
        return False
    except:
        logger.info("BOTCHECK PASSED")
    return True

async def create_order(page):
    
    await page.goto(BASKET_URL)
    
    try:
        await page.wait_for_selector("div.basket-form__basket-section.basket-section", timeout=20000)
    except TimeoutError:
        logger.info("DIV LOCATOR NOT FOUND")
    
    await asyncio.sleep(1)
    
    if await page.locator("label:has-text('Выбрать все')").count() == 1:
        logger.info("Выбрать всё is found")
        await page.locator("label:has-text('Выбрать все')").click()
        await page.locator("label.list-item__checkbox").first.click()
    else:
        logger.info("Выбрать всё is NOT found")
    
    if await page.locator("span.basket-order__link").count() == 1:
        logger.info("span.basket is found")
        await page.locator("span.basket-order__link").click()
        await page.locator(f"span.address-item__name-text:has-text('{cur_address}')").click()
        await page.get_by_role("button", name="Заберу отсюда").click()
    else:
        logger.info("span.basket is found")
    if await page.get_by_role("button", name="Заказать").count() > 0:
        logger.info("Заказать is found")
    else:
        logger.info("Заказать is NOT found")
    try:
        await page.get_by_role("button", name="Заказать").first.click() 
    except:
        logger.info("Main order button is not found, order wasn't complete")
        return False
    await asyncio.sleep(0.5)
    bank = page.locator("li.popup__banks-item:has-text('ПСБ')")
    if await bank.count() == 1:
        logger.info("bank is found")
        await bank.click()
    await asyncio.sleep(0.5)
    async with page.expect_request("**/submitorder**") as req_info:
        if await page.locator("button.btn-main", has_text="Да, заказать").count() == 1:
            logger.info("Да, заказать is found")
            await page.click("button.btn-main")
        if await page.locator("button.btn-main", has_text="Пополнить и заказать").count() == 1:
            logger.info("Пополнить и заказать is found")
            await page.click("button.btn-main")
        if await page.locator("button.popup__btn-main", has_text="Да, заказать").count() == 1:
            logger.info("Да, заказать is found")
            await page.click("button.popup__btn-main")
        if req_info.is_done():
            req_text = (req_info._future._result.post_data)
            order_rid = req_text[0][req_text[0].rfind("\r\n\r\n")+8:req_text[0].rfind(".0.0")+4]
            return order_rid
    return False

async def check_order(page):
    ...
    # with page.expect_request("**/submitorder**") as req_info:
    #     page.locator("button.j-btn-confirm-order").click()
    # request = req_info.value
    # print("Отправлен запрос:", request.url)

async def browser_close(context,browser):
    await context.close()
    await browser.close()

async def order_handler(acc_id,product_id):
    if not add_to_cart_handler(acc_id,product_id):
        return False
    async with async_playwright() as p:
        chrome_path = "C:/Program Files/Google/Chrome/Application/chrome.exe"
        browser = await p.chromium.launch(
            headless=NOT_TESTING,
            executable_path=chrome_path,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-first-run",
                "--disable-extensions",
                "--disable-default-apps",
                "--disable-popup-blocking",
                "--disable-background-networking",
                "--password-store=basic",
            ],
        )
        context = await browser.new_context(
            #Chrome User-Agent
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.6261.111 Safari/537.36"
            ),

            extra_http_headers={
                "sec-ch-ua": '"Chromium";v="122", "Google Chrome";v="122", "Not_A Brand";v="99"',
                "sec-ch-ua-platform": '"Windows"',
                "sec-ch-ua-platform-version": '"10.0.0"',
                "sec-ch-ua-arch": '"x86"',
                "sec-ch-ua-bitness": '"64"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-model": '""',
                "x-client-data": "CPiGywE=",
            },
        )
        
        page = await context.new_page()
        await page.goto(MAIN_PAGE_URL)

        await context.add_cookies(get_acc_cookies(acc_id))
        await page.evaluate(f"""
                localStorage.setItem('wbx__tokenData', '{json.dumps(get_acc_wbx_token(acc_id))}');
                """)
        await page.reload()

        

        logger.info(page)
        order_id = await create_order(page)
        await browser_close(context,browser)
        return order_id

if __name__ == "__main__":
    try:
        asyncio.get_event_loop()
    except:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    logger.info("If you see this, u MUST be in a debug session.\nCheck what file you are running!")
    NOT_TESTING = False
    acc_id = 0
    start = time.time()
    logger.info("task created")
    asyncio.run(order_handler(acc_id,367514477)) 
    logger.info(f"order was creating for {time.time()-start}")
