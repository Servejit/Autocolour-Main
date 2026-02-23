# ---------------------------------------------------
# INSTALL (Run once)
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
# 📂 EXCEL UPLOAD (ADDED FEATURE ONLY)

st.markdown("### 📂 Upload Excel for Score Analysis")

excel_file = st.file_uploader(
"Upload Excel File",
type=["xlsx"]
)

EXCEL_PATH="stock_scores.xlsx"

excel_df=None

if excel_file is not None:

    if os.path.exists(EXCEL_PATH):
        os.remove(EXCEL_PATH)

    with open(EXCEL_PATH,"wb") as f:
        f.write(excel_file.read())

    excel_df=pd.read_excel(EXCEL_PATH)

    excel_df["Stock"]=(
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

stockstar_list=[
s.strip().replace(".NS","")
for s in stockstar_input.split(",")
if s.strip()!=""
]

# ---------------------------------------------------
# SOUND SETTINGS (RESTORED)

sound_alert = st.toggle(
"🔊 Enable Alert Sound for -5% Green Stocks",
value=False
)

# ---------------------------------------------------
# TELEGRAM ALERT TOGGLE (RESTORED)

telegram_alert = st.toggle(
"📲 Enable Telegram Alert for Green Flashing",
value=False
)

# ---------------------------------------------------
# SOUND UPLOAD (RESTORED)

st.markdown("### 🎵 Alert Sound Settings")

uploaded_sound = st.file_uploader(
"Upload Your Custom Sound (.mp3 or .wav)",
type=["mp3","wav"]
)

DEFAULT_SOUND_URL="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3"

# ---------------------------------------------------
# STOCK LIST (ORIGINAL)

stocks={

"RELIANCE.NS":1402.25,
"TCS.NS":2578.54,
"HDFCBANK.NS":896.50,
"INFY.NS":1278.30,
"ITC.NS":400.00,
"LT.NS":3500.00,

}

# ---------------------------------------------------
# FETCH DATA

@st.cache_data(ttl=60)

def fetch_data():

    symbols=list(stocks.keys())

    data=yf.download(
    tickers=symbols,
    period="2d",
    interval="1d",
    group_by="ticker",
    progress=False
    )

    rows=[]

    for sym in symbols:

        try:

            ref=stocks[sym]

            price=data[sym]["Close"].iloc[-1]

            prev=data[sym]["Close"].iloc[-2]

            openp=data[sym]["Open"].iloc[-1]

            high=data[sym]["High"].iloc[-1]

            low=data[sym]["Low"].iloc[-1]

            p2l=((price-ref)/ref)*100

            chg=((price-prev)/prev)*100

            rows.append({

            "Stock":sym.replace(".NS",""),
            "P2L %":p2l,
            "Price":price,
            "% Chg":chg,
            "Low Price":ref,
            "Open":openp,
            "High":high,
            "Low":low

            })

        except:

            pass

    return pd.DataFrame(rows)

# ---------------------------------------------------
# BUTTONS (RESTORED)

col1,col2=st.columns(2)

with col1:

    if st.button("🔄 Refresh"):

        st.cache_data.clear()

        st.rerun()

with col2:

    sort_clicked=st.button("📈 Sort by P2L")

# ---------------------------------------------------
# LOAD DATA

df=fetch_data()

if excel_df is not None:

    df=df.merge(excel_df,on="Stock",how="left")

# ---------------------------------------------------
# SORT

if sort_clicked:

    df=df.sort_values("P2L %",ascending=False)

# ---------------------------------------------------
# GREEN TRIGGER (RESTORED)

green_trigger=False
trigger_stock=""
trigger_price=0
trigger_p2l=0

for _,row in df.iterrows():

    if row["Stock"] in stockstar_list and row["P2L %"]<-5:

        green_trigger=True
        trigger_stock=row["Stock"]
        trigger_price=row["Price"]
        trigger_p2l=row["P2L %"]

        break

# ---------------------------------------------------
# ALERT STATE

if "alert_played" not in st.session_state:

    st.session_state.alert_played=False

if not green_trigger:

    st.session_state.alert_played=False

# ---------------------------------------------------
# TELEGRAM ALERT (RESTORED)

if telegram_alert and green_trigger and not st.session_state.alert_played:

    current_time=datetime.now().strftime("%I:%M:%S %p")

    message=f"""

🟢 GREEN FLASH ALERT

Stock: {trigger_stock}

Price: ₹{trigger_price:.2f}

P2L: {trigger_p2l:.2f}%

Time: {current_time}

"""

    url=f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(url,data={

    "chat_id":CHAT_ID,

    "text":message

    })

# ---------------------------------------------------
# TABLE

def generate_html_table(dataframe):

    html="<table style='width:100%;border-collapse:collapse;'>"

    html+="<tr style='background-color:#111;'>"

    for col in dataframe.columns:

        html+=f"<th style='padding:8px;border:1px solid #444'>{col}</th>"

    html+="</tr>"

    for _,row in dataframe.iterrows():

        html+="<tr>"

        for col in dataframe.columns:

            value=row[col]

            style="padding:6px;border:1px solid #444;text-align:center;"

            # ORIGINAL STOCK COLOR

            if col=="Stock":

                if row["Stock"] in stockstar_list and row["P2L %"]<-5:

                    style+="color:green;font-weight:bold;animation: flash 1s infinite;"

                elif row["Stock"] in stockstar_list and row["P2L %"]<-3:

                    style+="color:orange;font-weight:bold;"

                elif row["P2L %"]<-2:

                    style+="color:hotpink;font-weight:bold;"

            # ORIGINAL CHANGE COLOR

            if col in ["P2L %","% Chg"]:

                if value>0:

                    style+="color:green;font-weight:bold;"

                elif value<0:

                    style+="color:red;font-weight:bold;"

            # EXCEL PRICE COLOR (ADDED ONLY)

            if col=="Price" and excel_df is not None:

                if pd.notna(row.get("Main6")) and row["Main6"]>=3:

                    style+="color:orange;font-weight:bold;"

                elif pd.notna(row.get("Main4")) and row["Main4"]>=2:

                    style+="color:hotpink;font-weight:bold;"

                elif pd.notna(row.get("Total")) and row["Total"]>=3:

                    style+="color:yellow;font-weight:bold;"

            if isinstance(value,float):

                value=f"{value:.2f}"

            html+=f"<td style='{style}'>{value}</td>"

        html+="</tr>"

    html+="</table>"

    return html

st.markdown(generate_html_table(df),unsafe_allow_html=True)

# ---------------------------------------------------
# SOUND ALERT (RESTORED)

if sound_alert and green_trigger and not st.session_state.alert_played:

    st.session_state.alert_played=True

    if uploaded_sound is not None:

        audio_bytes=uploaded_sound.read()

        b64=base64.b64encode(audio_bytes).decode()

        file_type=uploaded_sound.type

        st.markdown(f"""

<audio autoplay>

<source src="data:{file_type};base64,{b64}">

</audio>

""",unsafe_allow_html=True)

    else:

        st.markdown(f"""

<audio autoplay>

<source src="{DEFAULT_SOUND_URL}">

</audio>

""",unsafe_allow_html=True)

# ---------------------------------------------------
# AVERAGE

avg=df["P2L %"].mean()

st.markdown(f"### 📊 Average P2L of All Stocks is **{avg:.2f}%**")
