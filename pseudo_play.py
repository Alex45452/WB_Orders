# capture_and_replay_data_v2.py
import json
import time
import requests
from pprint import pprint
from playwright.sync_api import sync_playwright

# === Настройки ===
START_URL = "https://www.wildberries.ru/lk/basket"  # страница, где выполняется фронтенд и генерируются подписи
CAPTURE_TIMEOUT = 30  # сек, сколько ждать нужных запросов
# Если у тебя есть куки (авторизация), можно указать их в формате list of dicts (Playwright cookie format)
# Пример: [{"name":"_wb_token","value":"...","domain":".wildberries.ru","path":"/"}]
INITIAL_COOKIES = [
    {
        "name": "_wb_token",
        "value": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOjE3NjAwMDA4OTEsInVzZXIiOiIyMDExMDMwNjMiLCJzaGFyZF9rZXkiOiIyOSIsImNsaWVudF9pZCI6IndiIiwic2Vzc2lvbl9pZCI6IjNhZDE5ZDI5OTk1MjQ2MTg4NTlmNTFmYjAzYmNmNzYyIiwidmFsaWRhdGlvbl9rZXkiOiI4YjU0OGExNmUwYjc3NmI2NjlkOTQ5NjY5N2NlNTY2ZDA0NjE0MDliZDEyOGE5MTRlMTA1MThjYjRjYmI1NzgwIiwicGhvbmUiOiJ6djRRNW9vdTYvY3pEWlJTN2QySlV3PT0iLCJ1c2VyX3JlZ2lzdHJhdGlvbl9kdCI6MTczMzcxOTI1NSwidmVyc2lvbiI6Mn0.FmrhTVyBXt28O9Sa2shKjccTeTC5CIp82mM7rZyRGhUnRHXx57_rtXxN-M2HXATcEfWR9V3rXin-yiwB9vYTrIzz38cXcvJX3ms6ukha3NNmvcalhbGh3HduM92IkstsBkeWOo_9KJPnwRwXQ3bK9nThvMsW7a3esD1JUdPs3VMDg7StEsYpv74KpJYgAOYFVPuS-MNb0RPzzKwrAwZV0m_Ic9W56qWiUnu3BV9ax0jCrxjSIzDUSUTojSDYG3Zn_4dG983g7Lrrwwja8_1cw6dQTw9VdrXrQpuiMfMgQoD_gn73NOYc8CYsg27mhb3R4Q8BbHK4UYvXDMjDwMKN-Q",
        "domain": ".wildberries.ru",
        "path": "/",
        "httpOnly": True,
        "secure": True,
        "sameSite": "Lax",
        "expires": 1712345678
    },
    {
        "name": "deviceid",
        "value": "site_f5e2836af9d240778f074b34b31cd46f",
        "domain": ".wildberries.ru",
        "path": "/"
    }
]
# Список ключевых подстрок URL или полей, которые считаем "подписями"
SIGN_KEYS = [
    "userDataSign",
    "userBalanceSigned",
    "userGradeSigned",
    "customsDutySigned",
    "addressDataSign",
    "data_v2",
    "userBalance",
    "grade",
]

def capture_signatures_and_cookies(start_url=START_URL, timeout=CAPTURE_TIMEOUT, initial_cookies=INITIAL_COOKIES):
    found = {
        "requests": {},      # url -> postData (raw or parsed)
        "responses": {},     # url -> response text
        "localStorage": {},  # all localStorage
        "cookies": [],       # cookies from the browser
        "headers": {},       # example headers from captured request
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        if initial_cookies:
            context.add_cookies(initial_cookies)

        page = context.new_page()

        def on_request(req):
            try:
                url = req.url
                method = req.method
                post_data = req.post_data
                # Save requests that include any of sign keys in url or post_data
                if any(k in url for k in SIGN_KEYS) or (post_data and any(k in post_data for k in SIGN_KEYS)):
                    try:
                        # try to parse json if possible
                        parsed = None
                        if post_data:
                            try:
                                parsed = json.loads(post_data)
                            except Exception:
                                parsed = post_data
                        found["requests"][url] = parsed if parsed is not None else post_data
                        # save headers sample (first match)
                        if not found["headers"]:
                            hdrs = {}
                            for h in req.headers:
                                # copy only useful headers
                                if h.lower() in ("user-agent", "accept", "content-type", "referer", "origin", "deviceid", "x-requested-with"):
                                    hdrs[h] = req.headers[h]
                            found["headers"] = hdrs
                    except Exception as e:
                        print("on_request parse err:", e)
            except Exception:
                pass

        def on_response(resp):
            try:
                url = resp.url
                if any(k in url for k in SIGN_KEYS):
                    # try to get text, may be JSON
                    try:
                        txt = resp.text()
                    except Exception:
                        txt = "<no-text>"
                    found["responses"][url] = txt
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)

        # get localStorage after page load
        page.goto(start_url)
        # Wait a bit to let background requests happen
        start = time.time()
        while time.time() - start < timeout:
            # read localStorage each loop to catch runtime-set keys (like deviceid)
            try:
                ls = page.evaluate("() => Object.assign({}, window.localStorage)")
                found["localStorage"] = ls
            except Exception:
                pass
            # copy cookies currently in context
            try:
                found["cookies"] = context.cookies()
            except Exception:
                pass
            # break early if we found data_v2 and userDataSign or main signatures
            got_data_v2 = any("data_v2" in u for u in found["requests"].keys())
            got_userdatasign = any("userDataSign" in (json.dumps(v) if not isinstance(v, str) else v) for v in found["requests"].values())
            if got_data_v2 and got_userdatasign:
                break
            time.sleep(0.5)

        # close browser
        browser.close()

    return found

def build_and_send_data_v2(found, target_data_v2_url=None):
    """
    Takes captured objects and sends a POST to data_v2, using extracted signatures and cookies.
    """
    # 1) find captured data_v2 request body
    data_v2_url = None
    data_v2_payload = None
    for u, payload in found["requests"].items():
        if "data_v2" in u:
            data_v2_url = u
            data_v2_payload = payload
            break

    if target_data_v2_url:
        data_v2_url = target_data_v2_url

    if not data_v2_url:
        raise RuntimeError("Не найден захваченный запрос data_v2 в браузере.")

    # 2) If payload is raw JSON or string, ensure it's a dict
    body = None
    if isinstance(data_v2_payload, dict):
        body = data_v2_payload
    elif isinstance(data_v2_payload, str):
        try:
            body = json.loads(data_v2_payload)
        except Exception:
            # if it's not json (e.g., form-data raw), keep as text
            body = data_v2_payload

    # 3) Try to patch body with up-to-date signatures extracted elsewhere
    # If we captured userDataSign or others separately in requests, substitute them
    # Search through found["requests"] values for known sign fields and copy into body if present
    def find_field_in_requests(key):
        for payload in found["requests"].values():
            try:
                if isinstance(payload, dict) and key in payload:
                    return payload[key]
                if isinstance(payload, str) and key in payload:
                    # try to extract key=value pair from raw text
                    import re
                    m = re.search(rf"{key}=?([^&\\s]+)", payload)
                    if m:
                        return m.group(1)
            except Exception:
                pass
        return None

    # list of candidate keys in the body we want to update from captured ones
    candidate_keys = ["userDataSign", "userBalanceSigned", "userGradeSigned", "customsDutySigned", "addressDataSign"]
    if isinstance(body, dict):
        for k in candidate_keys:
            if k in body:
                new = find_field_in_requests(k)
                if new:
                    body[k] = new

    # 4) Prepare headers and cookies for requests
    headers = {k:v for k,v in found.get("headers", {}).items()}
    # remove any pseudo headers if present
    pseudo = [":method", ":path", ":authority", ":scheme"]
    for p in pseudo:
        headers.pop(p, None)

    # ensure proper content-type: if body is dict send as json, else send as text
    send_json = isinstance(body, dict)
    if send_json:
        headers.setdefault("content-type", "application/json")
    else:
        headers.setdefault("content-type", "text/plain")

    # convert Playwright cookies list to dict for requests
    cookie_dict = {}
    for c in found.get("cookies", []):
        cookie_dict[c.get("name")] = c.get("value")

    # 5) Send the request via requests
    print("-> Sending POST to:", data_v2_url)
    print("-> Headers to be sent:")
    pprint(headers)
    print("-> Cookies to be sent:")
    pprint(cookie_dict)
    print("-> Body preview:")
    if isinstance(body, dict):
        pprint({k: body[k] for k in list(body.keys())[:10]})
    else:
        print(body[:500] if isinstance(body, str) else str(body))

    if send_json:
        resp = requests.post(data_v2_url, headers=headers, cookies=cookie_dict, json=body)
    else:
        resp = requests.post(data_v2_url, headers=headers, cookies=cookie_dict, data=body)

    print("Status:", resp.status_code)
    try:
        print("Response JSON:")
        pprint(resp.json())
    except Exception:
        print("Response text:")
        print(resp.text)
    return resp

if __name__ == "__main__":
    print("1) Запускаем браузер и захватываем подписи и тело data_v2...")
    captured = capture_signatures_and_cookies()
    print("Захвачено ключевых элементов:")
    print("Requests:", len(captured["requests"]))
    print("Responses:", len(captured["responses"]))
    print("LocalStorage keys:", len(captured["localStorage"]))
    print("Cookies:", len(captured["cookies"]))
    print()

    # Для отладки сохраним в файл
    with open("captured_signs.json", "w", encoding="utf-8") as f:
        json.dump(captured, f, indent=2, ensure_ascii=False)

    print("2) Формируем и отправляем data_v2 с захваченными подписьми...")
    build_and_send_data_v2(captured)
