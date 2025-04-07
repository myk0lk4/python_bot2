import re
import asyncio
import requests
from telethon import TelegramClient, events
from pybit.unified_trading import HTTP
from config import api_key, api_secret, telegram_token, telegram_user_id

# Telegram API
api_id = 21519152
api_hash = 'a9f836e413b3b50b4adf20b46921c3e8'
session_name = 'torgobukva_session'
channel_url = -1002000727116

# Bybit API
session = HTTP(api_key=api_key, api_secret=api_secret, testnet=True)

client = TelegramClient(session_name, api_id, api_hash)

# 🔻 Обработка сигналов
@client.on(events.NewMessage(chats=channel_url))
async def handler(event):
    message = event.message.message
    print("\n📩 Сообщение:\n", message)
    send_telegram_message(f"📩 Новое сообщение в канале:\n{message}")

    try:
        pair = re.search(r'([A-Z]+USDT)', message).group(1)
        direction = 'SHORT' if 'SHORT' in message.upper() else 'LONG'
        leverage = int(re.search(r'(\d+)X', message).group(1))
        entry = float(re.search(r'Вход[:\s]*([0-9.]+)', message).group(1))
        stop = float(re.search(r'Стоп[:\s]*([0-9.]+)', message).group(1))
        take_section = message.split('Тейк')[1]
        takes = [float(t) for t in re.findall(r'[\d.]+', take_section)]

        print(f"✅ Пара: {pair}\nНаправление: {direction}\nПлечо: {leverage}\nEntry: {entry}\nStop: {stop}\nTPs: {takes}")
        await execute_trade(pair, direction, leverage, entry, stop, takes)

    except Exception as e:
        print("❌ Ошибка парсинга:", e)


# 🔻 Торговля
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    data = {"chat_id": telegram_user_id, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram notify error:", e)

async def execute_trade(symbol, direction, leverage, entry, stop_loss, take_profits):
    try:
        balance_info = session.get_wallet_balance(accountType="UNIFIED")
        usdt_balance = float(balance_info['result']['list'][0]['totalEquity'])

        risk_percent = 1.5
        position_value = usdt_balance * (risk_percent / 100)
        qty = round(position_value / entry, 3)

        side = "Sell" if direction.upper() == "SHORT" else "Buy"
        session.set_leverage(category="linear", symbol=symbol, buy_leverage=leverage, sell_leverage=leverage)

        order = session.place_order(
            category="linear",
            symbol=symbol,
            side=side,
            order_type="Market",
            qty=qty,
            time_in_force="GoodTillCancel",
            reduce_only=False
        )

        order_id = order['result']['orderId']
        send_telegram_message(f"✅ Сделка открыта: {symbol} {side}\nПлечо: {leverage}x\nОбъём: {qty}\nTP1: {take_profits[0]} | TP2: {take_profits[1]} | SL: {stop_loss}")

        tp1_qty = round(qty * 0.65, 3)
        tp2_qty = qty - tp1_qty

        opposite = "Buy" if side == "Sell" else "Sell"
        tp_orders = [
            {"price": take_profits[0], "qty": tp1_qty},
            {"price": take_profits[1], "qty": tp2_qty}
        ]

        for tp in tp_orders:
            session.place_order(
                category="linear",
                symbol=symbol,
                side=opposite,
                order_type="Limit",
                qty=tp['qty'],
                price=tp['price'],
                time_in_force="GoodTillCancel",
                reduce_only=True
            )

        session.set_trading_stop(
            category="linear",
            symbol=symbol,
            stop_loss=stop_loss
        )

    except Exception as e:
        print("❌ Ошибка трейда:", e)
        send_telegram_message(f"❌ Ошибка при открытии сделки: {e}")


# Главная функция
async def main():
    await client.start()

    print("🤖 Бот запущен и слушает канал...")
    await client.run_until_disconnected()



if __name__ == '__main__':
    asyncio.run(main())