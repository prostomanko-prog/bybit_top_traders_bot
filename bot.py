import os
import time
import telebot

from signals import generate_signals

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if TELEGRAM_TOKEN is None or CHAT_ID is None:
    raise RuntimeError("Missing TELEGRAM_TOKEN or CHAT_ID in Railway Variables")

CHAT_ID = int(CHAT_ID)

bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode="HTML")

CHECK_INTERVAL = 60  # проверяем раз в 60 сек


def send_signal(sig):
    text = (
        "🔥 <b>Сигнал от топ-трейдеров Bybit</b>\n\n"
        f"Монета: <b>{sig['symbol']}</b> (Perpetual)\n"
        f"Направление: <b>{sig['direction']}</b>\n"
        f"Цена входа: <b>{sig['entry']}</b>\n\n"
        f"Стоп-лосс: <b>{sig['sl']}</b> (≈ -1.5%)\n"
        f"Тейк-профит 1: <b>{sig['tp1']}</b> (≈ +2.5%)\n"
        f"Тейк-профит 2: <b>{sig['tp2']}</b> (≈ +4.0%)\n\n"
        f"Рекомендуемое плечо: <b>x{sig['leverage']}</b>\n"
        f"Топ-трейдеры: <b>{sig['long_votes']} LONG / {sig['short_votes']} SHORT</b>\n"
        f"⏱ {sig['time']} UTC"
    )
    bot.send_message(chat_id=CHAT_ID, text=text)


def main_loop():
    print("Bot started...", flush=True)
    last_direction = None

    while True:
        try:
            sigs = generate_signals()
            if sigs:
                sig = sigs[0]

                # антиспам — шлём только если направление поменялось
                if sig["direction"] != last_direction:
                    last_direction = sig["direction"]
                    send_signal(sig)

        except Exception as e:
            print("Error in main_loop:", repr(e), flush=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main_loop()