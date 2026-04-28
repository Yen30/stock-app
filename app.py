import re
from io import StringIO

import pandas as pd
import requests
import streamlit as st
import urllib3
import yfinance as yf

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="策略選股名版🔥", page_icon="🔥", layout="centered")
st.title("策略選股名版🔥")


# =========================
# 抓台股清單
# =========================
def _fetch_isin_table(str_mode: int):
    url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={str_mode}"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers, timeout=20, verify=False)
    res.encoding = "big5"

    df = pd.read_html(StringIO(res.text))[0]
    df.columns = df.iloc[0]
    df = df.iloc[1:]
    return df


def _extract_codes(df, suffix):
    codes = []

    industry_col = None
    for col in df.columns:
        if "產業" in str(col):
            industry_col = col
            break

    for i, val in enumerate(df.iloc[:, 0].astype(str)):
        m = re.match(r"^(\d{4})", val.strip())
        if not m:
            continue

        code = m.group(1)

        if industry_col:
            industry = str(df.iloc[i][industry_col])
            if (
                "生技" in industry or
                "醫療" in industry or
                "建材營造" in industry or
                "食品" in industry or
                "ETF" in industry or
                "金融" in industry or
                "保險" in industry or
                "觀光" in industry or
                "餐飲" in industry
            ):
                continue

        codes.append(code + suffix)

    return codes


@st.cache_data(ttl=3600)
def get_all_tickers():
    twse = _extract_codes(_fetch_isin_table(2), ".TW")
    tpex = _extract_codes(_fetch_isin_table(4), ".TWO")
    return sorted(list(set(twse + tpex)))


# =========================
# 抓資料：已修正多層欄位錯誤
# =========================
def get_data(ticker):
    try:
        df = yf.download(
            ticker,
            period="1y",
            progress=False,
            auto_adjust=False,
            threads=False
        )

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df.columns = [str(c).title() for c in df.columns]

        needed_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in needed_cols:
            if col not in df.columns:
                return None

        return df

    except Exception:
        return None


# =========================
# 策略1：突破股
# =========================
def s1(df):
    if df is None or len(df) < 130:
        return False

    df = df.copy()

    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA44"] = df["Close"].rolling(44).mean()

    df["V"] = df["Volume"] / 1000
    df["V5"] = df["V"].rolling(5).mean()
    df["V120"] = df["V"].rolling(120).mean()

    last = df.iloc[-1]
    prev60_high = df["Close"].shift(1).rolling(60).max().iloc[-1]

    return (
        pd.notna(last["MA5"]) and
        pd.notna(last["MA25"]) and
        pd.notna(last["MA44"]) and
        pd.notna(prev60_high) and
        last["Close"] > last["MA44"] and
        last["MA44"] > df["MA44"].iloc[-2] and
        last["MA25"] > last["MA44"] and
        last["V5"] > last["V120"] and
        last["V"] > 5000 and
        last["Close"] > prev60_high and
        last["Close"] / last["MA25"] < 1.12 and
        last["Close"] > last["MA5"]
    )


# =========================
# 策略2：轉強起漲股
# =========================
def s2(df):
    if df is None or len(df) < 100:
        return False

    df = df.copy()

    df["MA44"] = df["Close"].rolling(44).mean()
    df["V"] = df["Volume"] / 1000
    df["V5"] = df["V"].rolling(5).mean()

    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = df["EMA12"] - df["EMA26"]

    prev = df.iloc[-2]
    last = df.iloc[-1]

    return (
        pd.notna(prev["MA44"]) and
        pd.notna(last["MA44"]) and
        pd.notna(df["MA44"].iloc[-6]) and
        pd.notna(prev["DIF"]) and
        pd.notna(last["DIF"]) and
        prev["Close"] < prev["MA44"] and
        last["Close"] > last["MA44"] and
        last["MA44"] > df["MA44"].iloc[-6] and
        last["Close"] / last["MA44"] < 1.1 and
        last["V"] > last["V5"] and
        last["V"] > prev["V"] and
        prev["DIF"] < 0 and
        last["DIF"] > 0
    )


# =========================
# 策略3：箱型突破股
# =========================
def s3(df):
    if df is None or len(df) < 70:
        return False

    df = df.copy()

    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA44"] = df["Close"].rolling(44).mean()

    df["V"] = df["Volume"] / 1000
    df["V5"] = df["V"].rolling(5).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    high20_close = df["Close"].shift(1).rolling(20).max().iloc[-1]
    high20_price = df["High"].shift(1).rolling(20).max().iloc[-1]
    low20_price = df["Low"].shift(1).rolling(20).min().iloc[-1]

    if pd.isna(high20_close) or pd.isna(high20_price) or pd.isna(low20_price):
        return False

    box_range = (high20_price - low20_price) / low20_price

    return (
        pd.notna(last["MA25"]) and
        pd.notna(last["MA44"]) and
        pd.notna(df["MA44"].iloc[-4]) and
        pd.notna(last["V5"]) and
        pd.notna(prev["V5"]) and
        last["Close"] > high20_close * 1.03 and
        box_range < 0.15 and
        last["V"] > last["V5"] * 1.5 and
        prev["V"] < prev["V5"] and
        last["MA44"] > df["MA44"].iloc[-4] and
        last["Close"] / last["MA25"] < 1.15
    )


# =========================
# 主程式
# =========================
if st.button("開始掃描🔥"):
    tickers = get_all_tickers()
    results = []

    progress = st.progress(0)

    for i, ticker in enumerate(tickers):
        df = get_data(ticker)

        if df is None:
            progress.progress((i + 1) / len(tickers))
            continue

        hit1 = s1(df)
        hit2 = s2(df)
        hit3 = s3(df)

        score = int(hit1) + int(hit2) + int(hit3)

        if score > 0:
            results.append({
                "股票": ticker.replace(".TW", "").replace(".TWO", ""),
                "強度": score,
                "策略1突破": "✅" if hit1 else "",
                "策略2轉強": "✅" if hit2 else "",
                "策略3箱突": "✅" if hit3 else "",
            })

        progress.progress((i + 1) / len(tickers))

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values(by="強度", ascending=False).reset_index(drop=True)

        st.success(f"找到 {len(df_result)} 檔")
        st.dataframe(df_result, use_container_width=True, hide_index=True)
    else:
        st.warning("沒有符合條件的股票")
else:
    st.info("按下『開始掃描🔥』後開始選股")
