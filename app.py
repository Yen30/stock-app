import streamlit as st
import yfinance as yf
import pandas as pd

st.title("策略選股")

st.write("條件：股價在25日均線上 + 成交量過濾")

# 測試用股票（先不要全市場，避免太慢）
tickers = [
    "2330.TW", "2454.TW", "2317.TW", "2303.TW", "2382.TW",
    "3034.TW", "2376.TW", "3661.TW", "3443.TW", "3017.TW",
    "2603.TW", "2609.TW", "2615.TW", "2207.TW", "2002.TW"
]

def get_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", progress=False)
        if df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df.columns = [c.title() for c in df.columns]
        return df
    except:
        return None

def check_stock(df):
    if df is None or len(df) < 30:
        return None

    df["MA25"] = df["Close"].rolling(25).mean()

    last = df.iloc[-1]

    cond_price = (
        pd.notna(last["MA25"]) and
        last["Close"] > last["MA25"]
    )

    cond_volume = last["Volume"] > 1000000  # 約1000張

    if cond_price and cond_volume:
        return {
            "收盤價": round(float(last["Close"]), 2),
            "25MA": round(float(last["MA25"]), 2),
            "成交量": int(last["Volume"])
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
        st.dataframe(df_result)
    else:
        st.write("今天沒有符合條件的股票")
