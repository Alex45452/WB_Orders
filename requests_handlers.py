import httpx
import time
from settings import TOKEN, DEVICE_ID

DETAIL_URL = "https://card.wb.ru/cards/v4/detail"
ADD_URL = "https://cart-storage-api.wildberries.ru/api/basket/sync"


headers = {
    "accept": "*/*",
    "accept-language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
    "authorization": f"Bearer {TOKEN}",
    "content-type": "application/json",
    "priority": "u=1, i",
    "sec-ch-ua": "\"Google Chrome\";v=\"141\", \"Not?A_Brand\";v=\"8\", \"Chromium\";v=\"141\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
    "wb-apptype": "site"
}


def get_product_details_params(product_id):
    params = {
        "appType":1,
        "curr":"rub",
        "dest":1259570238,
        "spp":30,
        "hide_dtype":11,
        "ab_testing":"false",
        "ab_testing":"false",
        "lang":"ru",
        "nm":product_id
        }
    return params
    
def check_response_details(response):
    return response.status_code == 200 and len(response.json()) > 0

def get_main_params():
    params = {
        "ts":int(time.time()),
        "device_id":DEVICE_ID
        }
    return params

def get_main_data(response_details):
    data = [{
    "chrt_id":response_details.json()["products"][0]["sizes"][0]["optionId"],
    "quantity":1,
    "cod_1s":response_details.json()["products"][0]["id"], # product_id 
    "client_ts":int(time.time()),
    "op_type":1,
    "subject_id":response_details.json()["products"][0]["subjectId"],
    "currency":"RUB",
    "timezonemin":180,
    }]
    return data

def check_response_main(response):
    return response.status_code == 200
# Придумать проверку на успешный запрос, потому что исходя из тестов код ответа 200 не гарантирует добавление  

def add_to_cart_handler(product_id):
    response_details = httpx.get(url=DETAIL_URL,params=get_product_details_params(product_id),headers=headers)
    if check_response_details(response_details):
        main_response = httpx.post(url=ADD_URL,params=get_main_params(),headers=headers,json=get_main_data(response_details))
        return check_response_main(main_response)
    return False

if __name__ == "__main__":
    print("If you see this, u MUST be in a debug session.\nCheck what file you are running!")
