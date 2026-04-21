import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from io import StringIO

st.set_page_config(page_title="策略選股", layout="centered")

st.title("策略選股（全台股）")
st.write("條件：25MA上 + 5日均量黃金交叉60日均量 + 成交量>5000")

# =====================
# 取得台股清單
# =====================
@st.cache_data
def get_all_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    res = requests.get(url)
    res.encoding = "big5"

    df = pd.read_html(StringIO(res.text))[0]
    df.columns = df.iloc[0]
    df = df.iloc[1:]

    df = df[df["有價證券別"] == "股票"]
    df["代號"] = df["代號及名稱"].str.split("　").str[0]

    tickers = df["代號"].tolist()
    tickers = [t + ".TW" for t in tickers]

    return tickers

# =====================
# 抓資料
# =====================
def get_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df.columns = [str(c).title() for c in df.columns]
        return df
    except:
        return None

# =====================
# 條件判斷
# =====================
def check_stock(df):
    if df is None or len(df) < 70:
        return None

    df = df.copy()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["VMA5"] = df["Volume"].rolling(5).mean()
    df["VMA60"] = df["Volume"].rolling(60).mean()

    prev = df.iloc[-2]
    last = df.iloc[-1]

    cond_price = last["Close"] > last["MA25"]

    cond_volume_cross = (
        prev["VMA5"] < prev["VMA60"] and
        last["VMA5"] > last["VMA60"]
    )

    cond_liquidity = last["Volume"] > 5000

    if cond_price and cond_volume_cross and cond_liquidity:
        return {
            "收盤價": round(float(last["Close"]), 2),
            "25MA": round(float(last["MA25"]), 2),
            "成交量": int(last["Volume"]),
        }

    return None

# =====================
# 主程式
# =====================
if st.button("開始掃描（全市場）"):

    tickers = get_all_tickers()
    results = []

    progress = st.progress(0)

    for i, ticker in enumerate(tickers[:500]):  # ⚠️先限制500檔（避免爆掉）
        df = get_data(ticker)
        result = check_stock(df)

        if result:
            result["股票"] = ticker.replace(".TW", "")
            results.append(result)

        progress.progress((i + 1) / 500)

    if results:
        df_result = pd.DataFrame(results)
        st.dataframe(df_result)
    else:
        st.warning("今天沒有符合條件的股票")
