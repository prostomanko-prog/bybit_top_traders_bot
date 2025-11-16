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

# каждые 5 минут проверяем рынок
CHECK_INTERVAL = 300


def send_signal(sig):
    text = (
        "🔥 <b>Сигнал</b>\n\n"
        f"Монета: <b>{sig['symbol']}</b>\n"
        f"Направление: <b>{sig['direction']}</b>\n"
        f"Цена входа: <b>{sig['entry']}</b>\n\n"
        f"Стоп-лосс: <b>{sig['sl']}</b> (≈ -1.5%)\n"
        f"Тейк-профит 1: <b>{sig['tp1']}</b> (≈ +2.5%)\n"
        f"Тейк-профит 2: <b>{sig['tp2']}</b> (≈ +4.0%)\n\n"
        f"Рекомендуемое плечо: <b>x{sig['leverage']}</b>\n"
        f"RSI(14): <b>{sig['rsi']}</b>\n"
        f"EMA20: <b>{sig['ema_fast']}</b> | EMA50: <b>{sig['ema_slow']}</b>\n"
        f"⏱ {sig['time']} UTC"
    )
    bot.send_message(chat_id=CHAT_ID, text=text)
    print(f"Sent signal for {sig['symbol']} {sig['direction']}", flush=True)


def main_loop():
    print("Bot started...", flush=True)

    # 🔥 ТЕСТОВОЕ СООБЩЕНИЕ ПРИ СТАРТЕ
    try:
        bot.send_message(
            CHAT_ID,
            "🧪 Тест: Я работаю,заебал"
        )
        print("Test message sent", flush=True)
    except Exception as e:
        print("Error sending test message:", repr(e), flush=True)

    last_direction = {}  # последнее направление по каждой монете

    while True:
        try:
            sigs = generate_signals()
            for sig in sigs:
                sym = sig["symbol"]
                direction = sig["direction"]

                # антиспам — только если направление по монете изменилось
                if last_direction.get(sym) != direction:
                    last_direction[sym] = direction
                    send_signal(sig)

        except Exception as e:
            print("Error in main_loop:", repr(e), flush=True)

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main_loop()