import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# =====================================
# TELEGRAM
# =====================================

BOT_TOKEN = "TELEGRAM_TOKEN"
CHAT_ID = "1872530070"

def send_telegram(msg):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    r = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": msg
        }
    )

    print("Telegram:", r.status_code)

# =====================================
# SETTINGS
# =====================================

TOP_N = 5

MIN_VOL_RATIO = 3
MAX_VOL_RATIO = 5

MIN_DAYRET = 0.05          # 5%

MIN_VALUE = 20_000_000_000 # 20B

# =====================================
# PRIORITY WATCHLIST
# =====================================

WATCHLIST = {

    "CUAN.JK": 1.20,
    "BRPT.JK": 1.15,
    "BREN.JK": 1.15,
    "PTRO.JK": 1.10,
    "TPIA.JK": 1.10,

    "BNBR.JK": 1.10,
    "ENRG.JK": 1.10,
    "DEWA.JK": 1.10,

    "INDY.JK": 1.05,
    "ESSA.JK": 1.05,
    "ITMG.JK": 1.05
}

# =====================================
# UNIVERSE
# =====================================

TICKERS = [

    "ADRO.JK","ITMG.JK","PTBA.JK","HRUM.JK","INDY.JK",
    "MBAP.JK","MEDC.JK","ESSA.JK",

    "BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK",
    "BRIS.JK","BTPS.JK","BNGA.JK","BNII.JK",

    "TLKM.JK","ASII.JK","JSMR.JK",

    "ICBP.JK","INDF.JK","KLBF.JK",

    "CPIN.JK","JPFA.JK",

    "AKRA.JK","SMGR.JK","INTP.JK",

    "TKIM.JK","INKP.JK",

    "ERAA.JK","MAPI.JK","ACES.JK",

    "BREN.JK",
    "CUAN.JK",
    "BRPT.JK",
    "PTRO.JK",
    "TPIA.JK",

    "BNBR.JK",
    "ENRG.JK",
    "DEWA.JK",
    "VKTR.JK",

    "AMMN.JK",

    "ANTM.JK",
    "INCO.JK",
    "MDKA.JK",
    "UNTR.JK",

    "CLEO.JK",
    "WOOD.JK",

    "LSIP.JK",
    "SIMP.JK",

    "SMRA.JK",
    "PWON.JK",
    "CTRA.JK",
    "BSDE.JK",

    "TBIG.JK",
    "TOWR.JK",
    "MTEL.JK",

    "GOTO.JK",
    "BUKA.JK",

    "BUMI.JK",
    "SMMA.JK",
    "EXCL.JK"
]

# =====================================
# SCAN
# =====================================

results = []

today = datetime.now().strftime("%Y-%m-%d")

for ticker in TICKERS:

    try:

        print("Scanning", ticker)

        df = yf.download(
            ticker,
            period="3mo",
            auto_adjust=True,
            progress=False
        )

        if len(df) < 25:
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        close = float(df["Close"].iloc[-1])
        open_ = float(df["Open"].iloc[-1])
        volume = float(df["Volume"].iloc[-1])

        vol20 = float(
            df["Volume"]
            .rolling(20)
            .mean()
            .iloc[-1]
        )

        if vol20 <= 0:
            continue

        vol_ratio = volume / vol20

        day_ret = (close - open_) / open_

        value = close * volume

        # ==========================
        # FILTER
        # ==========================

        if vol_ratio < MIN_VOL_RATIO:
            continue

        if vol_ratio > MAX_VOL_RATIO:
            continue

        if day_ret < MIN_DAYRET:
            continue

        if value < MIN_VALUE:
            continue

        # ==========================
        # SCORE
        # ==========================

        score = vol_ratio * (day_ret * 100)

        if ticker in WATCHLIST:
            score *= WATCHLIST[ticker]

        results.append({

            "Ticker": ticker,
            "Price": round(close, 2),
            "DayRet": round(day_ret * 100, 2),
            "VolRatio": round(vol_ratio, 2),
            "ValueB": round(value / 1_000_000_000, 1),
            "Score": round(score, 2)

        })

    except Exception as e:

        print(ticker, e)

# =====================================
# OUTPUT
# =====================================

if len(results) == 0:

    msg = (
        f"⚡ OVERNIGHT SCANNER\n"
        f"📅 {today}\n\n"
        f"❌ No Overnight Setup"
    )

    print(msg)

    send_telegram(msg)

else:

    result_df = pd.DataFrame(results)

    result_df = result_df.sort_values(
        "Score",
        ascending=False
    )

    top = result_df.head(TOP_N)

    print("\n")
    print("=" * 70)
    print("TOP OVERNIGHT SETUP")
    print("=" * 70)

    print(top.to_string(index=False))

    msg = (
        f"⚡ OVERNIGHT SCANNER\n"
        f"📅 {today}\n\n"
    )

    rank = 1

    for _, row in top.iterrows():

        msg += (
            f"#{rank} {row['Ticker']}\n"
            f"DayRet   : {row['DayRet']}%\n"
            f"VolRatio : {row['VolRatio']}x\n"
            f"Value    : {row['ValueB']} B\n"
            f"Score    : {row['Score']}\n\n"
        )

        rank += 1

    print("\nSending Telegram...")

    send_telegram(msg)

print("DONE")
