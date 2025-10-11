from playwright.sync_api import sync_playwright
import json


# TIME = "2025-11-10T09:31:26.967Z"
WBX_KEY = "4770a1e8-ecfc-40de-a79a-ac00b1a2f40a"
TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjAwMDA4OTEsInVzZXIiOiIyMDExMDMwNjMiLCJzaGFyZF9rZXkiOiIyOSIsImNsaWVudF9pZCI6IndiIiwic2Vzc2lvbl9pZCI6IjNhZDE5ZDI5OTk1MjQ2MTg4NTlmNTFmYjAzYmNmNzYyIiwidmFsaWRhdGlvbl9rZXkiOiI4YjU0OGExNmUwYjc3NmI2NjlkOTQ5NjY5N2NlNTY2ZDA0NjE0MDliZDEyOGE5MTRlMTA1MThjYjRjYmI1NzgwIiwicGhvbmUiOiJ6djRRNW9vdTYvY3pEWlJTN2QySlV3PT0iLCJ1c2VyX3JlZ2lzdHJhdGlvbl9kdCI6MTczMzcxOTI1NSwidmVyc2lvbiI6Mn0.FmrhTVyBXt28O9Sa2shKjccTeTC5CIp82mM7rZyRGhUnRHXx57_rtXxN-M2HXATcEfWR9V3rXin-yiwB9vYTrIzz38cXcvJX3ms6ukha3NNmvcalhbGh3HduM92IkstsBkeWOo_9KJPnwRwXQ3bK9nThvMsW7a3esD1JUdPs3VMDg7StEsYpv74KpJYgAOYFVPuS-MNb0RPzzKwrAwZV0m_Ic9W56qWiUnu3BV9ax0jCrxjSIzDUSUTojSDYG3Zn_4dG983g7Lrrwwja8_1cw6dQTw9VdrXrQpuiMfMgQoD_gn73NOYc8CYsg27mhb3R4Q8BbHK4UYvXDMjDwMKN-Q"

cookies = [
    {
    "name": "wbx-validation-key",
    "value": WBX_KEY,
    "domain": ".wildberries.ru",
    "path": "/",
    "httponly": True,
    "secure": True,
    "sameSite": "Lax",
    # "expires": datetime.datetime.fromisoformat(TIME).timestamp()
    }
]


# wbx_token = {"token":TOKEN,"pvKey":None,"slideOff":None,"phone3":"792"}
wbx_token = {"token":TOKEN,"pvKey":None,"slideOff":None}


with sync_playwright() as p:
    
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()

    context.add_cookies(cookies)
    
    page = context.new_page()
    

    page.goto("https://wildberries.ru")
    
    page.evaluate(f"""
            localStorage.setItem('wbx__tokenData', '{json.dumps(wbx_token)}');
            """)
    
    
    page.reload()
    print(page)
    
    page.goto("https://wildberries.ru/lk/basket")

    page.wait_for_selector("label:has-text('Выбрать все')")

    # Кликаем по нему (клик по label активирует сам input)
    page.locator("label:has-text('Выбрать все')").click()
    page.locator("label.list-item__checkbox").first.click()
    page.get_by_role("button", name="Заказать").click()


    # with page.expect_request("**/data_v2**") as req_info:
    #     page.locator("button.j-btn-confirm-order").click()
    # request = req_info.value
    # print("Отправлен запрос:", request.url)
    context.close()
    browser.close()

    
    


    # _wbauid=9377879791754925670; wbx-validation-key=4770a1e8-ecfc-40de-a79a-ac00b1a2f40a; _ga=GA1.1.414966491.1758781886; _ga_TXRZMJQDFE=GS2.1.s1758976679$o2$g0$t1758976693$j46$l0$h0; routeb=1760054306.852.74.790085|3c1054d09865b256a0b95190d0b86bd8; _cp=1


    # wbx-validation-key=4770a1e8-ecfc-40de-a79a-ac00b1a2f40a
    # Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjAwMDA4OTEsInVzZXIiOiIyMDExMDMwNjMiLCJzaGFyZF9rZXkiOiIyOSIsImNsaWVudF9pZCI6IndiIiwic2Vzc2lvbl9pZCI6IjNhZDE5ZDI5OTk1MjQ2MTg4NTlmNTFmYjAzYmNmNzYyIiwidmFsaWRhdGlvbl9rZXkiOiI4YjU0OGExNmUwYjc3NmI2NjlkOTQ5NjY5N2NlNTY2ZDA0NjE0MDliZDEyOGE5MTRlMTA1MThjYjRjYmI1NzgwIiwicGhvbmUiOiJ6djRRNW9vdTYvY3pEWlJTN2QySlV3PT0iLCJ1c2VyX3JlZ2lzdHJhdGlvbl9kdCI6MTczMzcxOTI1NSwidmVyc2lvbiI6Mn0.FmrhTVyBXt28O9Sa2shKjccTeTC5CIp82mM7rZyRGhUnRHXx57_rtXxN-M2HXATcEfWR9V3rXin-yiwB9vYTrIzz38cXcvJX3ms6ukha3NNmvcalhbGh3HduM92IkstsBkeWOo_9KJPnwRwXQ3bK9nThvMsW7a3esD1JUdPs3VMDg7StEsYpv74KpJYgAOYFVPuS-MNb0RPzzKwrAwZV0m_Ic9W56qWiUnu3BV9ax0jCrxjSIzDUSUTojSDYG3Zn_4dG983g7Lrrwwja8_1cw6dQTw9VdrXrQpuiMfMgQoD_gn73NOYc8CYsg27mhb3R4Q8BbHK4UYvXDMjDwMKN-Q