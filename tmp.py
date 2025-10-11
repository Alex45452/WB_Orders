import json

HAR_PATH = "www.wildberries.ru.har"

def extract_cookies_from_har(har_path):
    with open(har_path, "r", encoding="utf-8") as f:
        har = json.load(f)
    cookies = []
    for entry in har["log"]["entries"]:
        for cookie in entry.get("request", {}).get("cookies", []):
            if cookie["name"] not in [c["name"] for c in cookies]:
                cookies.append({
                    "name": cookie["name"],
                    "value": cookie["value"],
                    "domain": ".wildberries.ru",
                    "path": "/",
                    "secure": True,
                    "httpOnly": False
                })
    return cookies

print(extract_cookies_from_har("./www.wildberries.ru.har"))