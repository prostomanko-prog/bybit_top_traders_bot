import requests
from datetime import datetime


# ==== НАСТРОЙКИ ====
SYMBOLS = {
    "BTCUSDT": "bitcoin",
    "ETHUSDT": "ethereum"
}

TF_SMALL = "5m"
TF_BIG = "15m"

SL_PCT = 0.01       # 1%
TP1_PCT = 0.015     # 1.5%
TP2_PCT = 0.025     # 2.5%
VOLUME_MULTIPLIER = 1.5
LEVERAGE = 5


# ==== API ИСТОЧНИК ====
# используем Binance Spot для OHLCV (так как объёмы доступны, и нет блоков)
BASE_URL = "https://api.binance.com/api/v3/klines"


def get_klines(symbol: str, interval: str, limit: int = 120):
    url = f"{BASE_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    data = r.json()
    closes = [float(x[4]) for x in data]
    volumes = [float(x[5]) for x in data]
    return closes, volumes


# ==== ТЕХАНАЛИЗ ====
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
        gains.append(max(0, diff))
        losses.append(max(0, -diff))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(values) - 1):
        diff = values[i + 1] - values[i]
        gain = max(diff, 0)
        loss = max(-diff, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values):
    ema12 = ema(values, 12)
    ema26 = ema(values, 26)
    macd_line = ema12 - ema26
    signal_line = ema(values[-35:], 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


# ==== БОЛЬШОЙ АЛГОРИТМ ====
def generate_signals():
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    signals = []

    for symbol in SYMBOLS.keys():
        try:
            closes_s, volumes_s = get_klines(symbol, TF_SMALL)
            closes_b, _ = get_klines(symbol, TF_BIG)
        except:
            continue

        if len(closes_s) < 60 or len(closes_b) < 60:
            continue

        # EMA на small TF
        ema20_prev = ema(closes_s[:-1], 20)
        ema50_prev = ema(closes_s[:-1], 50)
        ema20_curr = ema(closes_s, 20)
        ema50_curr = ema(closes_s, 50)

        # RSI
        rsi_val = rsi(closes_s, 14)
        if rsi_val is None:
            continue

        # MACD
        macd_line, signal_line, hist = macd(closes_s)

        # VOLUME FILTER
        avg_vol = sum(volumes_s[:-1]) / len(volumes_s[:-1])
        vol_ok = volumes_s[-1] > avg_vol * VOLUME_MULTIPLIER

        # BIG TREND (15m)
        ema20_big = ema(closes_b, 20)
        ema50_big = ema(closes_b, 50)

        big_trend = "LONG" if ema20_big > ema50_big else "SHORT"

        # ENTRY PRICE
        entry = closes_s[-1]

        direction = None

        # ==== LONG ====
        if (
            ema20_prev < ema50_prev and ema20_curr > ema50_curr and
            rsi_val > 55 and hist > 0 and
            big_trend == "LONG" and vol_ok
        ):
            direction = "LONG"

        # ==== SHORT ====
        if (
            ema20_prev > ema50_prev and ema20_curr < ema50_curr and
            rsi_val < 45 and hist < 0 and
            big_trend == "SHORT" and vol_ok
        ):
            direction = "SHORT"

        if direction:
            if direction == "LONG":
                sl = round(entry * (1 - SL_PCT), 2)
                tp1 = round(entry * (1 + TP1_PCT), 2)
                tp2 = round(entry * (1 + TP2_PCT), 2)
            else:
                sl = round(entry * (1 + SL_PCT), 2)
                tp1 = round(entry * (1 - TP1_PCT), 2)
                tp2 = round(entry * (1 - TP2_PCT), 2)

            signals.append({
                "symbol": symbol,
                "direction": direction,
                "entry": round(entry, 2),
                "sl": sl,
                "tp1": tp1,
                "tp2": tp2,
                "leverage": LEVERAGE,
                "rsi": round(rsi_val, 1),
                "macd_hist": round(hist, 4),
                "ema_fast": round(ema20_curr, 2),
                "ema_slow": round(ema50_curr, 2),
                "big_trend": big_trend,
                "volume_ok": vol_ok,
                "time": now
            })

    return signals