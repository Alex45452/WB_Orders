from playwright.async_api import async_playwright
from requests_handlers import add_to_cart_handler
from settings import ACCOUNTS, cur_address
import json
import time
import asyncio

MAIN_PAGE_URL = "https://wildberries.ru"
BASKET_URL = "https://wildberries.ru/lk/basket"

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

def get_acc_wbx_token(acc_id):
    wbx_token = {"token":ACCOUNTS[acc_id]["TOKEN"],"pvKey":None,"slideOff":None}
    return wbx_token

async def create_order(page):
    await page.goto(BASKET_URL)
    await page.wait_for_selector("div.basket-form__basket-section.basket-section", timeout=20000)
    await asyncio.sleep(1)
    if await page.locator("label:has-text('Выбрать все')").count() == 1:
        await page.locator("label:has-text('Выбрать все')").click()
        await page.locator("label.list-item__checkbox").first.click()
    if await page.locator("span.basket-order__link").count() == 1:
        await page.locator("span.basket-order__link").click()
        await page.locator(f"span.address-item__name-text:has-text('{cur_address}')").click()
        await page.get_by_role("button", name="Заберу отсюда").click()
    await page.get_by_role("button", name="Заказать").click()
    bank =  page.locator("li.popup__banks-item:has-text('ПСБ')")
    if await bank.count() == 1:
        await bank.click()
    if await page.locator("button.btn-main", has_text="Да, заказать").count() == 1:
        await page.click("button.btn-main")
    if await page.locator("button.popup__btn-main", has_text="Да, заказать").count() == 1:
        await page.click("button.popup__btn-main")

async def check_order(page):
    ...
    # with page.expect_request("**/data_v2**") as req_info:
    #     page.locator("button.j-btn-confirm-order").click()
    # request = req_info.value
    # print("Отправлен запрос:", request.url)

async def browser_close(context,browser):
    await context.close()
    await browser.close()

async def order_handler(acc_id):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()

        await context.add_cookies(get_acc_cookies(acc_id))
        
        page = await context.new_page()
        await page.goto(MAIN_PAGE_URL)

        await page.evaluate(f"""
                localStorage.setItem('wbx__tokenData', '{json.dumps(get_acc_wbx_token(acc_id))}');
                """)
        await page.reload()
        print(page)
        await create_order(page)
        await check_order(page) # todo
        await browser_close(context,browser)


if __name__ == "__main__":
    print("If you see this, u MUST be in a debug session.\nCheck what file you are running!")
    start = time.time()
    if add_to_cart_handler(283031138):
        asyncio.run(order_handler())
    print(time.time()-start)
