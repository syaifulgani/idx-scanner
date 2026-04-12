import yfinance as yf
import pandas as pd
import requests   
import os
from datetime import datetime

print("🚀 SCRIPT STARTED")

# ========================
# TELEGRAM CONFIG
# ========================
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    requests.post(url, data=payload)

# ========================
# LOAD TICKERS
# ========================
with open("idx_tickers.txt") as f:
    tickers = [line.strip() for line in f.readlines()]

print(f"Loaded {len(tickers)} tickers")

# ========================
# CONFIG STRATEGY 1
# ========================
TOP_N = 3
STOP_LOSS_PCT = 0.07
TAKE_PROFIT_PCT = 0.15

# ========================
# SCANNER
# ========================
results = []

for ticker in tickers:
    print(f"Scanning {ticker}...")

    try:
        data = yf.download(ticker, period="1y", progress=False)

        if data.empty or len(data) < 200:
            continue

        # Fix column issue
        data.columns = data.columns.get_level_values(0)

        # ========================
        # INDICATORS (STRATEGY 1)
        # ========================
        data['RET_60'] = data['Close'].pct_change(60)
        data['MA200'] = data['Close'].rolling(200).mean()
        data['VOL20'] = data['Volume'].rolling(20).mean()

        latest = data.iloc[-1]

        momentum = float(latest['RET_60'])
        price = float(latest['Close'])
        ma200 = float(latest['MA200'])
        volume = float(latest['Volume'])
        vol_avg = float(latest['VOL20'])

        if pd.isna(momentum) or pd.isna(ma200) or pd.isna(vol_avg):
            continue

        # ========================
        # STRATEGY 1 FILTER
        # ========================
        if price < ma200:
            continue

        if momentum < 0:
            continue

        if volume < vol_avg:
            continue

        # ========================
        # ENTRY / SL / TP
        # ========================
        entry = price
        sl = entry * (1 - STOP_LOSS_PCT)
        tp = entry * (1 + TAKE_PROFIT_PCT)

        rr = (tp - entry) / (entry - sl)

        results.append({
            "Ticker": ticker,
            "Entry": round(entry, 2),
            "SL": round(sl, 2),
            "TP": round(tp, 2),
            "Momentum": round(momentum, 4),
            "RR": round(rr, 2)
        })

    except Exception as e:
        print(f"Error {ticker}: {e}")

# ========================
# RANKING (IMPORTANT)
# ========================
df = pd.DataFrame(results)

today = datetime.now().strftime("%Y-%m-%d")

if not df.empty:
    df = df.sort_values("Momentum", ascending=False).head(TOP_N)

    print("\n🔥 TOP MOMENTUM SETUPS:")
    print(df)

    # Save Excel
    df.to_excel("strategy1_signals.xlsx", index=False)

    # ========================
    # TELEGRAM MESSAGE
    # ========================
    msg = f"🔥 {today} - STRATEGY 1 SIGNAL\n\n"

    for _, row in df.iterrows():
        msg += (
            f"*{row['Ticker']}*\n"
            f"Entry : {row['Entry']}\n"
            f"SL    : {row['SL']} (-7%)\n"
            f"TP    : {row['TP']} (+15%)\n"
            f"RR    : {row['RR']}\n"
            f"Mom   : {row['Momentum']:.2%}\n\n"
        )

    send_telegram(msg)

else:
    msg = f"📅 {today}\n❌ No Strategy 1 signal"
    print(msg)
    send_telegram(msg)

print("✅ DONE")
