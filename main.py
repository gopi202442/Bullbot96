import time
import requests
import yfinance as yf
import pandas as pd

# ======================
# CONFIG
# ======================
TELEGRAM_BOT_TOKEN = "7047129971:AAHnLUB7KeeFpnBW9IOJmOI8yxhjbL_fICY"
TELEGRAM_CHAT_ID = "1466420569"

INTERVAL = "5m"
PERIOD = "2d"
LOOP_INTERVAL = 15 * 60  # 15 minutes

# Example stock list (₹500 - ₹800)
STOCKS_500_800 = [
    "TATAMOTORS.NS", "AUROPHARMA.NS", "BHEL.NS", "BEL.NS", "CANBK.NS"
]

# ======================
# FUNCTIONS
# ======================
def send_telegram(msg: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def fetch_data(ticker: str):
    try:
        df = yf.download(ticker, interval=INTERVAL, period=PERIOD, progress=False)
        if df.empty:
            return None
        # EMAs
        for span in [5, 20, 50, 100, 200]:
            df[f"ema_{span}"] = df["Close"].ewm(span=span, adjust=False).mean()
        # RSI
        delta = df["Close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / avg_loss
        df["RSI"] = 100 - (100 / (1 + rs))
        return df
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def check_signals(df: pd.DataFrame, ticker: str):
    if df is None or len(df) < 20:
        return None

    last = df.iloc[-1]
    prev = df.iloc[-2]

    price = float(last["Close"])
    volume = float(last["Volume"])
    rsi = float(last["RSI"])

    signals = []

    for short, long in [(5, 20), (20, 50), (50, 100), (100, 200)]:
        prev_short = prev[f"ema_{short}"]
        prev_long = prev[f"ema_{long}"]
        last_short = last[f"ema_{short}"]
        last_long = last[f"ema_{long}"]

        # Bullish
        if prev_short <= prev_long and last_short > last_long and rsi > 60:
            stoploss = float(prev["Low"])
            target = price + 1.5 * (price - stoploss)
            signals.append(
                f"✅ Bullish Cross: EMA({short}) above EMA({long})\n"
                f"RSI: {rsi:.2f}\nStoploss: {stoploss:.2f}\nTarget: {target:.2f}"
            )

        # Bearish
        if prev_short >= prev_long and last_short < last_long and rsi < 35:
            stoploss = float(prev["High"])
            target = price - 1.5 * (stoploss - price)
            signals.append(
                f"❌ Bearish Cross: EMA({short}) below EMA({long})\n"
                f"RSI: {rsi:.2f}\nStoploss: {stoploss:.2f}\nTarget: {target:.2f}"
            )

    if signals:
        msg = (
            f"{ticker}\nPrice: {price:.2f}\nVolume: {volume:.0f}\n"
            + "\n".join(signals)
        )
        return msg
    return None

# ======================
# MAIN LOOP
# ======================
def main():
    while True:
        print(f"\nScanning {len(STOCKS_500_800)} tickers...")
        for ticker in STOCKS_500_800:
            df = fetch_data(ticker)
            if df is None:
                continue
            msg = check_signals(df, ticker)
            if msg:
                print(msg)
                send_telegram(msg)
            else:
                print(f"No signal for {ticker}")
        time.sleep(LOOP_INTERVAL)

if __name__ == "__main__":
    main()
