import os
import sys
import requests
import pandas as pd
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

API_KEY = os.environ["TWELVE_DATA_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
PAIRS = ["EUR/USD", "GBP/USD", "USD/JPY"]
NY = ZoneInfo("America/New_York")


def telegram_send(message: str):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    response = requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=20)
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError(f"Telegram error: {response.text}")


def get_candles(symbol: str, interval: str) -> pd.DataFrame:
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 100,
        "order": "ASC",
        "timezone": "UTC",
        "apikey": API_KEY,
    }
    response = requests.get(url, params=params, timeout=25)
    response.raise_for_status()
    payload = response.json()
    if "values" not in payload:
        raise RuntimeError(f"Market-data error for {symbol} ({interval}): {payload}")
    df = pd.DataFrame(payload["values"])
    for col in ["open", "high", "low", "close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.dropna().sort_values("datetime").reset_index(drop=True)
    # Exclude the newest candle because it may still be forming.
    if len(df) > 1:
        df = df.iloc[:-1].copy()
    return df


def indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema9"] = df.close.ewm(span=9, adjust=False).mean()
    df["ema21"] = df.close.ewm(span=21, adjust=False).mean()
    delta = df.close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    df["rsi"] = 100 - (100 / (1 + rs))
    previous_close = df.close.shift(1)
    tr = pd.concat([
        df.high - df.low,
        (df.high - previous_close).abs(),
        (df.low - previous_close).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.ewm(alpha=1/14, adjust=False).mean()
    return df


def analyze(symbol: str):
    m15 = indicators(get_candles(symbol, "15min"))
    h1 = indicators(get_candles(symbol, "1h"))
    if len(m15) < 60 or len(h1) < 60:
        return None

    current, previous = m15.iloc[-1], m15.iloc[-2]
    hourly = h1.iloc[-1]
    # Higher-timeframe trend filter.
    hourly_up = hourly.ema9 > hourly.ema21
    hourly_down = hourly.ema9 < hourly.ema21
    # Only alert on a fresh 15-minute EMA crossover, not every candle.
    crossed_up = previous.ema9 <= previous.ema21 and current.ema9 > current.ema21
    crossed_down = previous.ema9 >= previous.ema21 and current.ema9 < current.ema21
    rsi = float(current.rsi)
    atr = float(current.atr)
    entry = float(current.close)
    if pd.isna(atr) or atr <= 0 or pd.isna(rsi):
        return None

    if crossed_up and hourly_up and 50 <= rsi <= 68:
        direction = "BUY"
        stop = entry - 1.5 * atr
        target = entry + 3.0 * atr
    elif crossed_down and hourly_down and 32 <= rsi <= 50:
        direction = "SELL"
        stop = entry + 1.5 * atr
        target = entry - 3.0 * atr
    else:
        return None

    candle_time = current.datetime.strftime("%Y-%m-%d %H:%M UTC")
    digits = 3 if "JPY" in symbol else 5
    return (
        f"📊 FOREX SIGNAL — {direction}\n"
        f"Pair: {symbol}\n"
        f"Signal candle: {candle_time}\n"
        f"Entry reference: {entry:.{digits}f}\n"
        f"Stop-loss: {stop:.{digits}f}\n"
        f"Take-profit: {target:.{digits}f}\n"
        f"RSI(14): {rsi:.1f}\n"
        f"Setup: 15m EMA 9/21 crossover + 1h trend confirmation\n"
        f"Risk model: 1.5 ATR stop / 3 ATR target (2:1 planned R:R)\n\n"
        "Signal only — not a trade instruction. Check spread, news, and price before acting."
    )


def main():
    now = datetime.now(NY)
    if now.weekday() >= 5 or not (7 <= now.hour < 17):
        print("Outside configured weekday 7 AM–5 PM New York scan window.")
        return

    if "--test" in sys.argv:
        telegram_send("✅ Your Forex Signal Bot is connected. Test message successful. Signals only; no trades are placed.")
        print("Test message sent.")
        return

    for pair in PAIRS:
        try:
            signal = analyze(pair)
            if signal:
                telegram_send(signal)
                print(f"Sent signal for {pair}")
            else:
                print(f"No qualifying signal for {pair}")
        except Exception as exc:
            print(f"ERROR {pair}: {exc}")


if __name__ == "__main__":
    main()
