from datetime import datetime
import requests

from bybit_leaderboard import get_top_traders, BASE_URL

# Настройки
SYMBOL = "BTCUSDT"
CATEGORY = "linear"

SL_PCT = 0.015   # 1.5%
TP1_PCT = 0.025  # 2.5%
TP2_PCT = 0.04   # 4%
LEVERAGE = 5     # рекомендуемое плечо


def get_price(symbol=SYMBOL, category=CATEGORY):
    """
    Берём текущую цену по фьючам с Bybit.
    """
    url = f"{BASE_URL}/v5/market/tickers"
    params = {"category": category, "symbol": symbol}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()

    if data["retCode"] != 0:
        raise RuntimeError(f"Bybit price error: {data['retMsg']}")

    tick = data["result"]["list"][0]
    return float(tick["lastPrice"])


def generate_signals():
    """
    Логика:
    - Берём топ-трейдеров
    - Считаем, сколько за LONG / SHORT
    - Если >=3 в одну сторону и перевес — даём сигнал
    """

    signals = []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    try:
        traders = get_top_traders(limit=10)
    except Exception as e:
        print("Error load traders:", repr(e), flush=True)
        return signals

    long_votes = 0
    short_votes = 0

    for t in traders:
        side_raw = (t.get("side") or "").upper()  # BUY / SELL / LONG / SHORT
        if side_raw in ("BUY", "LONG"):
            long_votes += 1
        elif side_raw in ("SELL", "SHORT"):
            short_votes += 1

    direction = None
    if long_votes >= 3 and long_votes > short_votes:
        direction = "LONG"
    elif short_votes >= 3 and short_votes > long_votes:
        direction = "SHORT"

    if not direction:
        return signals

    try:
        price = get_price()
    except Exception as e:
        print("Error load price:", repr(e), flush=True)
        return signals

    entry = price

    if direction == "LONG":
        sl = round(entry * (1 - SL_PCT), 2)
        tp1 = round(entry * (1 + TP1_PCT), 2)
        tp2 = round(entry * (1 + TP2_PCT), 2)
    else:  # SHORT
        sl = round(entry * (1 + SL_PCT), 2)
        tp1 = round(entry * (1 - TP1_PCT), 2)
        tp2 = round(entry * (1 - TP2_PCT), 2)

    signals.append(
        {
            "symbol": SYMBOL,
            "direction": direction,
            "entry": round(entry, 2),
            "sl": sl,
            "tp1": tp1,
            "tp2": tp2,
            "leverage": LEVERAGE,
            "long_votes": long_votes,
            "short_votes": short_votes,
            "time": now,
        }
    )

    return signals