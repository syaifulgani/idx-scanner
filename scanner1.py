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

print("TOKEN:", BOT_TOKEN)
print("CHAT_ID:", CHAT_ID)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    requests.post(url, data=payload)

# ========================
# LOAD TICKERS
# ========================
with open("idx_tickers.txt") as f:
    tickers = [line.strip() for line in f.readlines()]

# ========================
# RSI FUNCTION
# ========================
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# ========================
# SCANNER
# ========================
results = []

for ticker in tickers:
    print(f"Scanning {ticker}...")

    try:
        data = yf.download(ticker, period="6mo", progress=False)

        if data.empty or len(data) < 50:
            continue

        # 🔥 FIX MULTI-INDEX
        data.columns = data.columns.get_level_values(0)

        # ========================
        # INDICATORS
        # ========================
        data['RSI'] = compute_rsi(data['Close'])
        data['VOL20'] = data['Volume'].rolling(20).mean()
        data['MA20'] = data['Close'].rolling(20).mean()

        # ========================
        # GET VALUES
        # ========================
        latest = data.iloc[-1]
        prev = data.iloc[-2]

        # Skip if NaN
        if pd.isna(latest['RSI']) or pd.isna(latest['VOL20']) or pd.isna(latest['MA20']):
            continue

        # Convert to float
        rsi = float(latest['RSI'])
        close = float(latest['Close'])
        prev_close = float(prev['Close'])
        volume = float(latest['Volume'])
        vol_avg = float(latest['VOL20'])
        ma20 = float(latest['MA20'])

        # ========================
        # BREAK OF STRUCTURE (BOS)
        # ========================
        recent_high = float(data['High'].rolling(10).max().iloc[-2])
        bos_up = close > recent_high

        # ========================
        # TRADINGVIEW MATCH LOGIC
        # ========================
        score = 0

        # RSI oversold
        if rsi < 30:
            score += 2

        # Price reversal
        if close > prev_close:
            score += 1

        # Volume spike
        if volume > 1.5 * vol_avg:
            score += 2

        # BOS confirmation
        if bos_up:
            score += 3

        # Trend filter (downtrend)
        if close < ma20:
            score += 1


         # ========================
        # ENTRY / SL / TP
        # ========================
        recent_low = float(data['Low'].rolling(5).min().iloc[-1])

        entry = close
        sl = recent_low
        risk = entry - sl

        if risk <= 0:
            continue

        # ========================
        # RISK FILTER (ADD HERE 🔥)
        # ========================

        risk_pct = risk / entry

        if risk_pct > 0.08:   # 8% max risk
            continue

        # TP1 (50% exit)
        tp1 = entry + (1 * risk)

        # Trailing stop (MA20)
        trail_sl = ma20
        if trail_sl < entry:
            trail_sl = entry


        # ========================
        # FINAL FILTER
        # ========================
        if score >= 5:
            results.append({
                "Ticker": ticker,
                "Entry": round(entry, 2),
                "SL": round(sl, 2),
                "TP1": round(tp1, 2),
                "Trail_SL": round(trail_sl, 2),
                "RSI": round(rsi, 2),
                "Score": score
            })

    except Exception as e:
        print(f"Error {ticker}: {e}")


# ========================
# OUTPUT
# ========================
df = pd.DataFrame(results)

today = datetime.now().strftime("%Y-%m-%d")

if not df.empty:
    df = df.sort_values("Score", ascending=False)

    print("\n🔥 TOP REVERSAL SETUPS:")
    print(df)

    # Save Excel
    df.to_excel("reversal_tv_match.xlsx", index=False)

    # Telegram message
    msg = f"📅 {today}\n🔥 REVERSAL + TREND SETUP\n\n"

    for _, row in df.iterrows():
        msg += (
            f"{row['Ticker']}\n"
            f"Entry: {row['Entry']}\n"
            f"SL: {row['SL']}\n"
            f"TP1 (50%): {row['TP1']}\n"
            f"Trail SL: {row['Trail_SL']}\n"
            f"Score: {row['Score']}\n\n"
        )

    send_telegram(msg)

else:
    msg = f"📅 {today}\n❌ No strong TradingView match signals today"
    print(msg)
    send_telegram(msg)

print("✅ DONE")
