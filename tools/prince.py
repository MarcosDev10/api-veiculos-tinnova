import redis
import requests

cache = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)


class Price:
    def __init__(self):
        self.base_url_principal = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
        self.base_url_fallback = "https://api.frankfurter.dev/v1/latest?from=USD&to=BRL"

    # Obtém os dados da api e salva em cache no redis
    def get_price(self):
        price = cache.get("price")
        if price:
            return True, price

        response = requests.get(self.base_url_principal)

        if response.status_code == 200:
            payload = response.json()
            cache.set("price",payload["USDBRL"]["high"], ex=300)
            return True, payload["USDBRL"]["high"]
        else:
            response_fallback = requests.get(self.base_url_fallback)

            if response_fallback.status_code == 200:
                payload = response_fallback.json()
                cache.set("price",payload["rates"]["BRL"], ex=300)
                return True, payload["rates"]["BRL"]
            else:
                return False, response_fallback.text

    # Faz a conversão dos valores de BRL para USD e USD para BRL
    def convert_to(self, value, to):
        _, prince = self.get_price()
        if _:
            if to == "brl_to_usd":
                amount = value / float(prince)
            elif to == "usd_to_brl":
                amount = value * float(prince)
            return round(amount, 2)
        else:
            return False
