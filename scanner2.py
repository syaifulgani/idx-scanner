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
# CATEGORY UNIVERSE
# ========================
CORE = [
    "ADRO.JK","ITMG.JK","PTBA.JK","HRUM.JK","INDY.JK","MBAP.JK","MEDC.JK","ESSA.JK",
    "CPIN.JK","JPFA.JK","ERAA.JK","MAPI.JK","ACES.JK",
    "SMGR.JK","INTP.JK","AKRA.JK","TPIA.JK","TKIM.JK",
    "BRIS.JK","BTPS.JK","BNGA.JK","BNII.JK","DEWA.JK"
]

STABILITY = [
    "BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK",
    "TLKM.JK","ASII.JK",
    "ICBP.JK","INDF.JK","KLBF.JK","JSMR.JK"
]

ALL_TICKERS = list(set(CORE + STABILITY))

print(f"Total stocks: {len(ALL_TICKERS)}")

def get_category(ticker):
    if ticker in CORE:
        return "CORE"
    else:
        return "STABILITY"

# ========================
# CONFIG (BEST STRATEGY)
# ========================
TOP_N = 3
STOP_LOSS_PCT = 0.07
TAKE_PROFIT_PCT = 0.18
MOM_THRESHOLD = 0.05

# ========================
# SCANNER
# ========================
results = []

for ticker in ALL_TICKERS:
    print(f"Scanning {ticker}...")

    try:
        data = yf.download(ticker, period="1y", progress=False)

        if data.empty or len(data) < 200:
            continue

        data.columns = data.columns.get_level_values(0)

        # ========================
        # INDICATORS
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

        if vol_avg == 0 or ma200 == 0:
            continue

        # ========================
        # FILTER (BEST STRATEGY)
        # ========================
        if price < ma200:
            continue

        if momentum < MOM_THRESHOLD:
            continue

        if volume < vol_avg:
            continue

        # 🔥 ADD QUALITY FILTER (IMPORTANT)
        volume_ratio = volume / vol_avg
        if volume_ratio < 1.2:
            continue

        # ========================
        # ENTRY / SL / TP
        # ========================
        entry = price
        sl = entry * (1 - STOP_LOSS_PCT)
        tp = entry * (1 + TAKE_PROFIT_PCT)

        rr = (tp - entry) / (entry - sl)

        category = get_category(ticker)

        results.append({
            "Ticker": ticker,
            "Entry": round(entry, 2),
            "SL": round(sl, 2),
            "TP": round(tp, 2),
            "Momentum": momentum,
            "VolRatio": round(volume_ratio, 2),
            "RR": round(rr, 2),
            "Category": category
        })

    except Exception as e:
        print(f"Error {ticker}: {e}")

# ========================
# RANKING + SELECTION
# ========================
df = pd.DataFrame(results)
today = datetime.now().strftime("%Y-%m-%d")

if not df.empty:

    # 🔥 SORT BY MOMENTUM (KEEP SIMPLE)
    df = df.sort_values("Momentum", ascending=False)

    # 🔥 CATEGORY SELECTION
    core_df = df[df['Category'] == 'CORE'].head(2)
    stable_df = df[df['Category'] == 'STABILITY'].head(1)

    top = pd.concat([core_df, stable_df])

    print("\n🔥 FINAL PICKS:")
    print(top)

    # Save Excel
    top.to_excel("strategy_signals.xlsx", index=False)

    # ========================
    # TELEGRAM MESSAGE
    # ========================
    msg = f"🔥 {today} - MOMENTUM SIGNAL (BEST STRATEGY)\n\n"

    for _, row in top.iterrows():
        msg += (
            f"*{row['Ticker']}* ({row['Category']})\n"
            f"Entry : {row['Entry']}\n"
            f"SL    : {row['SL']} (-7%)\n"
            f"TP    : {row['TP']} (+18%)\n"
            f"RR    : {row['RR']}\n"
            f"Mom   : {row['Momentum']:.2%}\n"
            f"Vol   : {row['VolRatio']}x\n"
            f"➡️ Manage:\n"
            f"   • BE @ +8%\n"
            f"   • Trail @ +15%\n\n"
        )

    send_telegram(msg)

else:
    msg = f"📅 {today}\n❌ No valid setup"
    print(msg)
    send_telegram(msg)

print("✅ DONE")
