"""
restore_session_from_har.py

1) Читает HAR-файл (по пути HAR_PATH)
2) Ищет в нём:
   - Authorization: Bearer ... (в заголовках)
   - wbx-validation-key (в request.cookies или response.set-cookie)
   - userId / uid / user_id
   - deviceid / deviceId
   - user-uuid / uuid
   - spp, dest, currency, xInfo, userDataSign (в body/params/text)
3) Запускает Playwright, ставит найденные cookies и localStorage значения,
   перезагружает страницу и открывает корзину.
"""

import json
import re
from urllib.parse import parse_qs, unquote
from pathlib import Path
from pprint import pprint

HAR_PATH = "www.wildberries.ru.har"  # <- при необходимости поменяй
TARGET_URL = "https://www.wildberries.ru/lk/basket"
PLAYWRIGHT_HEADLESS = False  # для отладки ставь False

# -----------------------------
# Парсинг HAR
# -----------------------------
def load_har(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def normalize_cookie_header(cookie_header: str):
    """Возвращает dict из строки Cookie: 'a=1; b=2' -> {'a':'1', 'b':'2'}"""
    out = {}
    if not cookie_header:
        return out
    parts = cookie_header.split(";")
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip()] = v.strip()
    return out

def extract_tokens_from_har(har):
    """
    Извлекает токен авторизации, куки из всех возможных мест (request.headers, request.cookies, response.set-cookie).
    """
    found = {
        "authorization": None,
        "cookies": {},
        "set_cookies": {},
        "bodies_text": [],
    }

    entries = har.get("log", {}).get("entries", [])
    for e in entries:
        req = e.get("request", {})

        # --- Ищем токен авторизации в заголовках ---
        for h in req.get("headers", []):
            name = h.get("name", "").lower()
            val = h.get("value", "")
            if name == "authorization" and not found["authorization"]:
                found["authorization"] = val.strip()
            elif name == "cookie":
                # разбираем куки
                found["cookies"].update(normalize_cookie_header(val))

        # --- HAR cookies ---
        for c in req.get("cookies", []):
            if c.get("name"):
                found["cookies"][c["name"]] = c.get("value", "")

        # --- POST / RESPONSE BODY ---
        post = req.get("postData", {})
        if post.get("text"):
            found["bodies_text"].append(post["text"])

        resp = e.get("response", {})
        # --- Проверяем заголовки Set-Cookie ---
        for h in resp.get("headers", []):
            if h.get("name", "").lower() == "set-cookie":
                val = h.get("value", "")
                parts = re.split(r",(?=[^;]+=)", val)
                for p in parts:
                    m = re.match(r"\s*([^=;\s]+)=([^;]+)", p)
                    if m:
                        name, value = m.group(1), m.group(2)
                        found["set_cookies"][name] = value

        # --- Тело ответа ---
        content = resp.get("content", {})
        if content.get("text"):
            found["bodies_text"].append(content["text"])

    # --- Попытка найти токен в теле (если не найден в заголовках) ---
    if not found["authorization"]:
        for t in found["bodies_text"]:
            m = re.search(r'Authorization["\']?\s*[:=]\s*["\']?(Bearer\s+[A-Za-z0-9\-\._]+)', t)
            if m:
                found["authorization"] = m.group(1)
                break
            m = re.search(r'Bearer\s+([A-Za-z0-9\-\._]+)', t)
            if m:
                found["authorization"] = "Bearer " + m.group(1)
                break

    # --- Подстраховка: иногда WB кладёт токен в cookie ---
    for k, v in found["cookies"].items():
        if "bearer" in v.lower() or len(v) > 80:
            found["authorization"] = "Bearer " + v
            break

    return found


# -----------------------------
# Поиск конкретных полей в урлах/текстах
# -----------------------------
def search_kv_in_texts(texts, patterns):
    """
    Ищет паттерны в массиве текстов.
    patterns: dict key->regex (regex should have a capturing group for value)
    Возвращает dict найденных значений (first match wins).
    """
    res = {}
    for key, regex in patterns.items():
        pat = re.compile(regex, re.IGNORECASE)
        for t in texts:
            if not t:
                continue
            for m in pat.finditer(t):
                val = m.group(1)
                # clean quotes
                val = val.strip().strip('"').strip("'")
                if val:
                    res[key] = val
                    break
            if key in res:
                break
    return res

def extract_common_keys(found):
    texts = found["bodies_text"][:]
    if found["cookies"]:
        texts.append(";".join(f"{k}={v}" for k,v in found["cookies"].items()))
    if found["set_cookies"]:
        texts.append(";".join(f"{k}={v}" for k,v in found["set_cookies"].items()))

    patterns = {
        "userId": r'\buserId["=:\s]+["\']?(\d{5,})["\']?',
        "uuid": r'\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\b',
        "deviceid": r'\b[a-f0-9]{12,}\b',
        "spp": r'\bspp=(\d{1,3})\b',
        "dest": r'\bdest=(\d{6,12})\b',
        "currency": r'\bcurr=([a-zA-Z]{3})\b',
        "xInfo": r'appType=\d+&curr=[a-zA-Z]+&dest=\d+&spp=\d+',
        "userDataSign": r'version=\d+&uid=\d+&spp=\d+&timestamp=\d+&sign=[a-f0-9]+',
    }

    found_kv = {}
    for key, regex in patterns.items():
        for text in texts:
            m = re.search(regex, text)
            if m:
                found_kv[key] = m.group(1) if m.groups() else m.group(0)
                break

    # фильтрация "мусора" (кусочков JS)
    for k, v in list(found_kv.items()):
        if len(v) > 200 or any(x in v for x in ["Error", "await", "throw", "resp_", "{", "}", "=>"]):
            del found_kv[k]

    # Добавим wbx-validation-key, если найден в куках
    for name, val in {**found["cookies"], **found["set_cookies"]}.items():
        if name.lower() == "wbx-validation-key":
            found_kv["wbx-validation-key"] = val

    return found_kv


# -----------------------------
# Построение Playwright сценария (runtime)
# -----------------------------
def run_playwright_with_extracted(extracted, har_cookies_map):
    # Lazy import to avoid requiring Playwright unless running this step
    from playwright.sync_api import sync_playwright
    # Prepare cookies list for context.add_cookies (domain must be .wildberries.ru)
    cookies_list = []
    for name, value in {**har_cookies_map, **extracted.get("cookie_overrides", {})}.items():
        if value is None or value == "":
            continue
        cookies_list.append({
            "name": name,
            "value": value,
            "domain": ".wildberries.ru",
            "path": "/",
            "httpOnly": False,
            "secure": True,
        })

    # Also ensure wbx-validation-key is present if found in set_cookies
    if "wbx-validation-key" in extracted.get("set_cookies", {}):
        cookies_list.append({
            "name": "wbx-validation-key",
            "value": extracted["set_cookies"]["wbx-validation-key"],
            "domain": ".wildberries.ru",
            "path": "/",
            "httpOnly": True,
            "secure": True,
        })

    print("Cookies to add (sample):")
    pprint(cookies_list[:10])

    # localStorage items to set
    ls_items = {}
    # Map discovered fields into localStorage keys that WB likely checks
    if extracted.get("authorization"):
        # may store token as 'Authorization' or 'auth-token'
        ls_items["Authorization"] = extracted["authorization"]
        ls_items["auth-token"] = extracted["authorization"].replace("Bearer ", "") if extracted["authorization"].startswith("Bearer") else extracted["authorization"]
    # deviceid
    if extracted.get("deviceid"):
        ls_items["deviceId"] = extracted["deviceid"]
        ls_items["deviceid"] = extracted["deviceid"]
    # userId / uuid / spp / dest / currency / xInfo / userDataSign
    for k in ("userId", "uuid", "spp", "dest", "currency", "xInfo", "userDataSign"):
        if extracted.get(k):
            ls_items[k] = extracted[k]

    print("LocalStorage items to set (sample):")
    pprint(ls_items)

    # Launch Playwright and inject
    # with sync_playwright() as p:
    #     browser = p.chromium.launch(headless=PLAYWRIGHT_HEADLESS)
    #     context = browser.new_context()
    #     if cookies_list:
    #         try:
    #             context.add_cookies(cookies_list)
    #         except Exception as e:
    #             print("Warning: add_cookies failed:", e)
    #     page = context.new_page()

    #     # go to base domain to be able to set localStorage
    #     page.goto("https://www.wildberries.ru", wait_until="domcontentloaded")

    #     # set localStorage keys
    #     if ls_items:
    #         for k, v in ls_items.items():
    #             # ensure string
    #             if v is None: continue
    #             safe_v = v.replace("'", "\\'")
    #             js = f"localStorage.setItem('{k}', '{safe_v}');"
    #             try:
    #                 page.evaluate(js)
    #             except Exception as e:
    #                 print("Failed to set localStorage", k, e)

    #     # reload and open basket
    #     page.reload()
    #     page.goto(TARGET_URL)
    #     # wait a bit and print some info
    #     page.wait_for_timeout(6000)
    #     # optional: print some localStorage keys back
    #     storage = page.evaluate("() => ({ localStorage: Object.assign({}, window.localStorage) })")
    #     print(">>> LocalStorage snapshot keys:")
    #     pprint(list(storage["localStorage"].keys())[:50])
    #     browser.close()

# -----------------------------
# Main
# -----------------------------
def main():
    har_file = Path(HAR_PATH)
    if not har_file.exists():
        print("HAR file not found:", HAR_PATH)
        return

    print("Loading HAR:", HAR_PATH)
    har = load_har(HAR_PATH)
    found = extract_tokens_from_har(har)

    # first try to find Authorization from request headers / bodies
    auth = found.get("authorization")
    if not auth:
        # try to find Bearer in bodies_text
        for t in found["bodies_text"]:
            if not t: continue
            m = re.search(r'Authorization"\s*:\s*"([^"]+)"', t)
            if m:
                auth = m.group(1); break
            m = re.search(r'Bearer\s+([A-Za-z0-9\-_\.]+)', t)
            if m:
                auth = "Bearer " + m.group(1); break
    if auth:
        print("Found Authorization:", auth[:80] + ("..." if len(auth) > 80 else ""))
    else:
        print("Authorization not found in HAR.")

    # merge cookies & set_cookies
    har_cookies_map = {}
    har_cookies_map.update(found.get("cookies", {}))
    har_cookies_map.update(found.get("set_cookies", {}))

    # attempt to extract other common keys from bodies
    extracted_kv = extract_common_keys(found)
    # include authorization and cookie maps into extracted for later use
    extracted_kv["authorization"] = auth
    extracted_kv["cookies_map"] = har_cookies_map
    extracted_kv["set_cookies"] = found.get("set_cookies", {})
    # print short report
    print("\n=== Report (found) ===")
    print("Cookies (sample):")
    pprint({k:har_cookies_map[k] for k in list(har_cookies_map)[:20]})
    print("Extracted key-values:")
    pprint(extracted_kv)

    # run playwright to set cookies/localStorage and open basket
    run_playwright_with_extracted(extracted_kv, har_cookies_map)

if __name__ == "__main__":
    main()
