import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="策略選股", layout="centered")

st.title("策略選股")
st.write("條件：股價在 25 日均線上 + 10 日均量線金叉 60 日均量線")

tickers = [
    "2330.TW", "2454.TW", "2317.TW", "2303.TW", "2382.TW",
    "3034.TW", "2376.TW", "3661.TW", "3443.TW", "3017.TW",
    "2603.TW", "2609.TW", "2615.TW", "2207.TW", "2002.TW"
]

def get_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False, auto_adjust=False)
        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df.columns = [str(c).title() for c in df.columns]
        return df
    except Exception:
        return None

def check_stock(df):
    if df is None or len(df) < 70:
        return None

    df = df.copy()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["VMA10"] = df["Volume"].rolling(10).mean()
    df["VMA60"] = df["Volume"].rolling(60).mean()

    prev = df.iloc[-2]
    last = df.iloc[-1]

    # 改這裡：不用剛突破，只要站在 25MA 上
    cond_price_above = (
        pd.notna(last["MA25"]) and
        last["Close"] > last["MA25"]
    )

    # 保留原本量能金叉條件
    cond_volume_cross = (
        pd.notna(prev["VMA10"]) and pd.notna(prev["VMA60"]) and
        pd.notna(last["VMA10"]) and pd.notna(last["VMA60"]) and
        prev["VMA10"] <= prev["VMA60"] and
        last["VMA10"] > last["VMA60"]
    )

    # 可選：排除太小量
    cond_liquidity = last["Volume"] > 1000000

    if cond_price_above and cond_volume_cross and cond_liquidity:
        return {
            "股票": "",
            "收盤價": round(float(last["Close"]), 2),
            "25MA": round(float(last["MA25"]), 2),
            "成交量": int(last["Volume"]),
            "10日均量": int(last["VMA10"]),
            "60日均量": int(last["VMA60"]),
        }

    return None

if st.button("開始選股"):
    results = []

    for ticker in tickers:
        df = get_data(ticker)
        result = check_stock(df)

        if result:
            result["股票"] = ticker.replace(".TW", "")
            results.append(result)

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result[["股票", "收盤價", "25MA", "成交量", "10日均量", "60日均量"]]
        st.dataframe(df_result, use_container_width=True)
    else:
        st.write("今天沒有符合條件的股票")
