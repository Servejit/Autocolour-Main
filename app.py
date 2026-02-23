# ---------------------------------------------------
# INSTALL (Run once in terminal)
# pip install streamlit yfinance pandas requests openpyxl
# ---------------------------------------------------

import streamlit as st
import yfinance as yf
import pandas as pd
import base64
import requests
from datetime import datetime
import os

st.set_page_config(page_title="📊 Live Stock P2L", layout="wide")
st.title("📊 Live Prices with P2L")

# ---------------------------------------------------
# TELEGRAM SETTINGS

BOT_TOKEN = "YOUR_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

# ---------------------------------------------------
# FLASHING CSS

st.markdown("""
<style>
@keyframes flash {
    0% { opacity: 1; }
    50% { opacity: 0.2; }
    100% { opacity: 1; }
}
table {
    background-color:#0e1117;
    color:white;
}
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------
# 📂 EXCEL UPLOAD FEATURE (ADDED)

st.markdown("### 📂 Upload Excel for Score Analysis")

excel_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx"]
)

EXCEL_PATH = "stock_scores.xlsx"

excel_df = None

if excel_file is not None:

    if os.path.exists(EXCEL_PATH):
        os.remove(EXCEL_PATH)

    with open(EXCEL_PATH, "wb") as f:
        f.write(excel_file.read())

    excel_df = pd.read_excel(EXCEL_PATH)

    excel_df["Stock"] = (
        excel_df["Stock"]
        .astype(str)
        .str.replace(".NS","")
        .str.upper()
    )

# ---------------------------------------------------
# STOCKSTAR INPUT

stockstar_input = st.text_input(
    "⭐ StockStar (Comma Separated)",
    "BOSCHLTD.NS, BSE.NS, HEROMOTOCO.NS, HINDALCO.NS, HINDZINC.NS, M&M.NS, MUTHOOTFIN.NS, PIIND.NS"
).upper()

stockstar_list = [
    s.strip().replace(".NS", "")
    for s in stockstar_input.split(",")
    if s.strip() != ""
]

# ---------------------------------------------------
# SOUND SETTINGS

sound_alert = st.toggle("🔊 Enable Alert Sound for -5% Green Stocks", value=False)

# ---------------------------------------------------
# TELEGRAM ALERT TOGGLE

telegram_alert = st.toggle("📲 Enable Telegram Alert for Green Flashing", value=False)

# ---------------------------------------------------
# SOUND UPLOAD

st.markdown("### 🎵 Alert Sound Settings")

uploaded_sound = st.file_uploader(
    "Upload Your Custom Sound (.mp3 or .wav)",
    type=["mp3", "wav"]
)

DEFAULT_SOUND_URL = "https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"

# ---------------------------------------------------
# STOCK LIST

stocks = {

    "ADANIENT.NS": 2092.68,
    "ADANIGREEN.NS": 957.19,
    "ADANIPORTS.NS": 1487.82,
    "AMBUJACEM.NS": 506.11,
    "AXISBANK.NS": 1309.52,
    "BAJAJHFL.NS": 88.23,
    "BHARTIARTL.NS": 1961.15,
    "BHEL.NS": 249.45,
    "BOSCHLTD.NS": 35043.90,
    "BPCL.NS": 367.20,
    "BSE.NS": 2718.29,
    "CANBK.NS": 139.45,
    "COALINDIA.NS": 404.57,
    "COFORGE.NS": 1330.67,
    "DIXON.NS": 10540.58,
    "DLF.NS": 612.92,
    "DMART.NS": 3823.09,
    "ETERNAL.NS": 264.19,
    "GMRAIRPORT.NS": 93.06,
    "GODREJCP.NS": 1165.94,
    "HCLTECH.NS": 1392.51,
    "HDFCAMC.NS": 2687.89,
    "HDFCBANK.NS": 896.50,
    "HEROMOTOCO.NS": 5419.27,
    "HINDALCO.NS": 878.80,
    "HINDUNILVR.NS": 2282.38,
    "HINDZINC.NS": 573.56,
    "IDFCFIRSTB.NS": 79.61,
    "INDHOTEL.NS": 661.68,
    "INDUSINDBK.NS": 907.39,
    "INFY.NS": 1278.30,
    "IRCTC.NS": 603.12,
    "IRFC.NS": 110.02,
    "JIOFIN.NS": 258.25,
    "JSWENERGY.NS": 466.51,
    "JUBLFOOD.NS": 522.62,
    "KOTAKBANK.NS": 416.16,
    "LODHA.NS": 1052.06,
    "LTIM.NS": 4741.18,
    "M%26M.NS": 3444.69,
    "MANKIND.NS": 2004.83,
    "MOTHERSON.NS": 127.84,
    "MPHASIS.NS": 2288.17,
    "MUTHOOTFIN.NS": 3348.18,
    "NAUKRI.NS": 1049.13,
    "NHPC.NS": 73.34,
    "OBEROIRLTY.NS": 1486.53,
    "OFSS.NS": 6384.00,
    "OIL.NS": 451.02,
    "PAGEIND.NS": 32302.68,
    "PERSISTENT.NS": 4903.71,
    "PFC.NS": 395.26,
    "PHOENIXLTD.NS": 1693.49,
    "PIIND.NS": 2999.93,
    "PNB.NS": 116.96,
    "POLYCAB.NS": 7498.32,
    "PRESTIGE.NS": 1464.64,
    "RECLTD.NS": 338.10,
    "RELIANCE.NS": 1402.25,
    "SHREECEM.NS": 25621.25,
    "SOLARINDS.NS": 12787.74,
    "SRF.NS": 2609.39,
    "SUZLON.NS": 43.61,
    "TATACONSUM.NS": 1111.51,
    "TATASTEEL.NS": 199.55,
    "TCS.NS": 2578.54,
    "TECHM.NS": 1422.85,
    "TRENT.NS": 4019.80,
    "ULTRACEMCO.NS": 12515.11,
    "UPL.NS": 712.82,
    "VBL.NS": 443.37,
    "YESBANK.NS": 20.60,
}

# ---------------------------------------------------
# FETCH DATA

@st.cache_data(ttl=60)
def fetch_data():

    symbols = list(stocks.keys())

    data = yf.download(
        tickers=symbols,
        period="2d",
        interval="1d",
        group_by="ticker",
        progress=False,
        threads=True
    )

    rows = []

    for sym in symbols:

        try:

            ref_low = stocks[sym]

            price = data[sym]["Close"].iloc[-1]
            prev_close = data[sym]["Close"].iloc[-2]
            open_p = data[sym]["Open"].iloc[-1]
            high = data[sym]["High"].iloc[-1]
            low = data[sym]["Low"].iloc[-1]

            p2l = ((price - ref_low) / ref_low) * 100
            pct_chg = ((price - prev_close) / prev_close) * 100

            rows.append({
                "Stock": sym.replace(".NS", ""),
                "P2L %": p2l,
                "Price": price,
                "% Chg": pct_chg,
                "Low Price": ref_low,
                "Open": open_p,
                "High": high,
                "Low": low
            })

        except:
            pass

    return pd.DataFrame(rows)

# ---------------------------------------------------
# LOAD DATA

df = fetch_data()

# merge excel

if excel_df is not None:
    df = df.merge(excel_df, on="Stock", how="left")

# ---------------------------------------------------
# ORIGINAL TABLE WITH EXCEL COLOR ADDITION

def generate_html_table(dataframe):

    html = """
    <table style="width:100%; border-collapse: collapse;">
    <tr style="background-color:#111;">
    """

    for col in dataframe.columns:
        html += f"<th style='padding:8px; border:1px solid #444;'>{col}</th>"

    html += "</tr>"

    for _, row in dataframe.iterrows():

        html += "<tr>"

        for col in dataframe.columns:

            value = row[col]

            style = "padding:6px; border:1px solid #444; text-align:center;"

            # ORIGINAL COLORS

            if col == "Stock":

                if row["Stock"] in stockstar_list and row["P2L %"] < -5:

                    style += "color:green; font-weight:bold; animation: flash 1s infinite;"

                elif row["Stock"] in stockstar_list and row["P2L %"] < -3:

                    style += "color:orange; font-weight:bold;"

                elif row["P2L %"] < -2:

                    style += "color:hotpink; font-weight:bold;"


            if col in ["P2L %", "% Chg"]:

                if value > 0:

                    style += "color:green; font-weight:bold;"

                elif value < 0:

                    style += "color:red; font-weight:bold;"


            # EXCEL PRICE COLOR

            if col == "Price" and excel_df is not None:

                if pd.notna(row.get("Main6")) and row["Main6"] >= 3:

                    style += "color:orange; font-weight:bold;"

                elif pd.notna(row.get("Main4")) and row["Main4"] >= 2:

                    style += "color:hotpink; font-weight:bold;"

                elif pd.notna(row.get("Total")) and row["Total"] >= 3:

                    style += "color:yellow; font-weight:bold;"


            if isinstance(value, float):

                value = f"{value:.2f}"

            html += f"<td style='{style}'>{value}</td>"

        html += "</tr>"

    html += "</table>"

    return html


st.markdown(generate_html_table(df), unsafe_allow_html=True)

# ---------------------------------------------------

average_p2l = df["P2L %"].mean()

st.markdown(
    f"### 📊 Average P2L of All Stocks is **{average_p2l:.2f}%**"
)
