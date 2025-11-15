import requests

BASE_URL = "https://api.bybit.com"

def get_top_traders(category="linear", limit=10):
    """
    Bybit API: Top Traders Position Data
    В ответе приходит список топ-трейдеров и их сторона (BUY/SELL).
    """
    url = f"{BASE_URL}/v5/position/leaders"
    params = {
        "category": category,
        "limit": limit
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    if data["retCode"] != 0:
        raise RuntimeError(f"Bybit error: {data['retMsg']}")

    return data["result"]["list"]
