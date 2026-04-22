import re
from io import StringIO

import pandas as pd
import requests
import streamlit as st
import urllib3
import yfinance as yf

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="策略選股", page_icon="📈", layout="centered")

st.title("策略選股（全台股）")
st.write("條件：44MA上揚 + 5日均量>120日均量 + 成交量>5000張 + 創20日新高 + 不追高")


# =========================
# 抓台股清單
# =========================
def _fetch_isin_table(str_mode: int) -> pd.DataFrame:
    url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={str_mode}"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers, timeout=20, verify=False)
    res.encoding = "big5"

    tables = pd.read_html(StringIO(res.text))
    if not tables:
        return pd.DataFrame()

    df = tables[0].copy()

    if len(df) > 0:
        first_row = df.iloc[0].astype(str).tolist()
        if any("代號" in x for x in first_row):
            df.columns = first_row
            df = df.iloc[1:].copy()

    df.columns = [str(c).strip() for c in df.columns]
    return df


def _extract_codes(df: pd.DataFrame, suffix: str) -> list[str]:
    if df.empty:
        return []

    first_col = df.columns[0]
    codes = []

    for val in df[first_col].astype(str):
        m = re.match(r"^(\d{4})", val.strip())
        if m:
            codes.append(f"{m.group(1)}{suffix}")

    return sorted(list(set(codes)))


@st.cache_data(ttl=3600)
def get_twse_tickers():
    df = _fetch_isin_table(2)
    return _extract_codes(df, ".TW")


@st.cache_data(ttl=3600)
def get_tpex_tickers():
    df = _fetch_isin_table(4)
    return _extract_codes(df, ".TWO")


@st.cache_data(ttl=3600)
def get_all_tickers():
    return sorted(list(set(get_twse_tickers() + get_tpex_tickers())))


# =========================
# 抓股價資料
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
            df.columns = [c[0] for c in df.columns]

        df.columns = [str(c).title() for c in df.columns]
        return df
    except Exception:
        return None


# =========================
# 條件判斷
# =========================
def check_stock(df):
    if df is None or len(df) < 130:
        return None

    df = df.copy()

    # 均線
    df["MA44"] = df["Close"].rolling(44).mean()
    df["MA44_prev"] = df["MA44"].shift(1)

    df["MA25"] = df["Close"].rolling(25).mean()

    # 成交量
    df["Volume張"] = df["Volume"] / 1000
    df["VMA5"] = df["Volume張"].rolling(5).mean()
    df["VMA120"] = df["Volume張"].rolling(120).mean()

    last = df.iloc[-1]

    # 條件
    cond_price = last["Close"] > last["MA44"]
    cond_ma_up = last["MA44"] > last["MA44_prev"]
    cond_volume = last["VMA5"] > last["VMA120"]
    cond_liquidity = last["Volume張"] > 5000
    cond_break = last["Close"] >= df["Close"].rolling(20).max().iloc[-1]

    # 🔥 不追高條件
    cond_not_too_far = last["Close"] / last["MA25"] < 1.2

    if cond_price and cond_ma_up and cond_volume and cond_liquidity and cond_break and cond_not_too_far:
        return {
            "股票": "",
            "收盤價": round(float(last["Close"]), 2),
            "44日線": round(float(last["MA44"]), 2),
            "25日線": round(float(last["MA25"]), 2),
            "乖離": round(float(last["Close"] / last["MA25"]), 2),
            "成交量(張)": int(last["Volume張"]),
        }

    return None


# =========================
# 主程式
# =========================
if st.button("開始選股"):
    tickers = get_all_tickers()

    st.write(f"掃描 {len(tickers)} 檔股票")

    progress = st.progress(0)
    results = []

    for i, t in enumerate(tickers):
        df = get_data(t)
        r = check_stock(df)

        if r:
            r["股票"] = t.replace(".TW", "").replace(".TWO", "")
            results.append(r)

        progress.progress((i + 1) / len(tickers))

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values(by="成交量(張)", ascending=False).reset_index(drop=True)

        st.success(f"找到 {len(df_result)} 檔")
        st.dataframe(df_result, use_container_width=True, hide_index=True)
    else:
        st.warning("今天沒有符合條件的股票")
else:
    st.info("按下『開始選股』後開始掃描。")
