from playwright.sync_api import sync_playwright
import json
import settings

MAIN_PAGE_URL = "https://wildberries.ru"
BASKET_URL = "https://wildberries.ru/lk/basket"


def create_order(page):
    page.goto(BASKET_URL)
    page.wait_for_selector("label:has-text('Выбрать все')")
    page.locator("label:has-text('Выбрать все')").click()
    page.locator("label.list-item__checkbox").first.click()
    if page.locator("span.basket-order__link").count() == 1:
        page.locator("span.basket-order__link").click()
        page.locator("span.address-item__name-text:has-text('поселение Воскресенское,   40к1')").click()
        page.get_by_role("button", name="Заберу отсюда").click()
    page.get_by_role("button", name="Заказать").click()

def check_order(page):
    ...
    # with page.expect_request("**/data_v2**") as req_info:
    #     page.locator("button.j-btn-confirm-order").click()
    # request = req_info.value
    # print("Отправлен запрос:", request.url)

def browser_close(context,browser):
    context.close()
    browser.close()

def order_handler():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()

        context.add_cookies(settings.cookies)
        
        page = context.new_page()
        page.goto(MAIN_PAGE_URL)

        page.evaluate(f"""
                localStorage.setItem('wbx__tokenData', '{json.dumps(settings.wbx_token)}');
                """)
        page.reload()
        print(page)

        create_order(page)
        check_order(page)
        browser_close(context,browser)

if __name__ == "__main__":
    print("If you see this, u MUST be in a debug session.\nCheck what file you are running!")
    order_handler()