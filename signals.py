from datetime import datetime
import requests

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Монеты: бинанский стиль тикера -> CoinGecko id
COINS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum",
}

SL_PCT = 0.015   # 1.5%
TP1_PCT = 0.025  # 2.5%
TP2_PCT = 0.04   # 4.0%
LEVERAGE = 5     # рекомендуемое плечо


def get_prices(coin_id: str, vs_currency: str = "usd", days: int = 1):
    """
    Берём историю цен с CoinGecko за N дней.
    Возвращаем список close-цен.
    """
    url = f"{COINGECKO_BASE}/coins/{coin_id}/market_chart"
    params = {"vs_currency": vs_currency, "days": days}
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()
    prices = [p[1] for p in data.get("prices", [])]
    return prices


def ema(values, period):
    k = 2 / (period + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def rsi(values, period=14):
    if len(values) < period + 1:
        return None

    gains = []
    losses = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        if diff >= 0:
            gains.append(diff)
            losses.append(0.0)
        else:
            gains.append(0.0)
            losses.append(-diff)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(values) - 1):
        diff = values[i + 1] - values[i]
        gain = max(diff, 0.0)
        loss = max(-diff, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1 + rs)


def generate_signals():
    """
    Для каждой монеты:
    - тянем историю цен
    - считаем EMA20/EMA50
    - ищем пересечение + фильтр по RSI
    - формируем сигнал LONG/SHORT, SL/TP
    """
    signals = []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    for symbol, coin_id in COINS.items():
        try:
            closes = get_prices(coin_id, days=1)
        except Exception as e:
            print(f"Error load prices for {symbol}:", repr(e), flush=True)
            continue

        if len(closes) < 60:
            continue

        # предыдущие и текущие EMA
        ema20_prev = ema(closes[:-1], 20)
        ema50_prev = ema(closes[:-1], 50)
        ema20_curr = ema(closes, 20)
        ema50_curr = ema(closes, 50)

        rsi_val = rsi(closes, 14)
        if rsi_val is None:
            continue

        price = closes[-1]

        direction = None
        # пересечение вверх + RSI бычий
        if ema20_prev < ema50_prev and ema20_curr > ema50_curr and rsi_val > 55:
            direction = "LONG"
        # пересечение вниз + RSI медвежий
        elif ema20_prev > ema50_prev and ema20_curr < ema50_curr and rsi_val < 45:
            direction = "SHORT"

        if not direction:
            continue

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
                "symbol": symbol,
                "direction": direction,
                "entry": round(entry, 2),
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "leverage": LEVERAGE,
                "rsi": round(rsi_val, 1),
                "ema_fast": round(ema20_curr, 2),
                "ema_slow": round(ema50_curr, 2),
                "time": now,
            }
        )

    return signals