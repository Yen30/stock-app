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
st.write("條件：股價在25日均線上 + 5日均量線黃金交叉60日均量線 + 成交量大於5000張")


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

    # 有些頁面第一列是表頭
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
def get_twse_tickers() -> list[str]:
    df = _fetch_isin_table(2)   # 上市
    return _extract_codes(df, ".TW")


@st.cache_data(ttl=3600)
def get_tpex_tickers() -> list[str]:
    df = _fetch_isin_table(4)   # 上櫃
    return _extract_codes(df, ".TWO")


@st.cache_data(ttl=3600)
def get_all_tickers() -> list[str]:
    tickers = get_twse_tickers() + get_tpex_tickers()
    return sorted(list(set(tickers)))


# =========================
# 抓股價資料
# =========================
def get_data(ticker: str):
    try:
        df = yf.download(
            ticker,
            period="8mo",
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
def check_stock(df: pd.DataFrame):
    if df is None or len(df) < 70:
        return None

    df = df.copy()
    df["MA25"] = df["Close"].rolling(25).mean()

    # 台股成交量改成「張」
    df["Volume張"] = df["Volume"] / 1000

    # 均量也用「張」計算
    df["VMA5"] = df["Volume張"].rolling(5).mean()
    df["VMA60"] = df["Volume張"].rolling(60).mean()

    prev = df.iloc[-2]
    last = df.iloc[-1]

    # 1. 股價在25日均線上
    cond_price_above = (
        pd.notna(last["MA25"]) and
        last["Close"] > last["MA25"]
    )

    # 2. 5日均量線今天上穿60日均量線，且昨天還在下方
    cond_volume_cross = (
        pd.notna(prev["VMA5"]) and pd.notna(prev["VMA60"]) and
        pd.notna(last["VMA5"]) and pd.notna(last["VMA60"]) and
        prev["VMA5"] < prev["VMA60"] and
        last["VMA5"] > last["VMA60"]
    )

    # 3. 成交量大於5000張
    cond_liquidity = (
        pd.notna(last["Volume張"]) and
        last["Volume張"] > 5000
    )

    if cond_price_above and cond_volume_cross and cond_liquidity:
        return {
            "股票": "",
            "收盤價": round(float(last["Close"]), 2),
            "25日均線": round(float(last["MA25"]), 2),
            "成交量(張)": int(last["Volume張"]),
            "5日均量(張)": int(last["VMA5"]),
            "60日均量(張)": int(last["VMA60"]),
        }

    return None


# =========================
# UI
# =========================
scan_mode = st.selectbox(
    "掃描範圍",
    ["先掃 100 檔（最快）", "掃 300 檔", "全部台股（較慢）"],
    index=0
)

if scan_mode == "先掃 100 檔（最快）":
    limit = 100
elif scan_mode == "掃 300 檔":
    limit = 300
else:
    limit = None


if st.button("開始選股"):
    try:
        tickers = get_all_tickers()
    except Exception as e:
        st.error(f"取得台股清單失敗：{e}")
        st.stop()

    if not tickers:
        st.error("抓不到台股清單，請稍後再試。")
        st.stop()

    if limit is not None:
        tickers = tickers[:limit]

    st.write(f"本次掃描：{len(tickers)} 檔")
    progress_bar = st.progress(0)
    status_text = st.empty()

    results = []

    for i, ticker in enumerate(tickers):
        status_text.text(f"掃描中：{ticker} ({i+1}/{len(tickers)})")

        df = get_data(ticker)
        result = check_stock(df)

        if result:
            result["股票"] = ticker.replace(".TW", "").replace(".TWO", "")
            results.append(result)

        progress_bar.progress((i + 1) / len(tickers))

    status_text.text("掃描完成")

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result[
            ["股票", "收盤價", "25日均線", "成交量(張)", "5日均量(張)", "60日均量(張)"]
        ]
        df_result = df_result.sort_values(by="成交量(張)", ascending=False).reset_index(drop=True)

        st.success(f"找到 {len(df_result)} 檔符合條件的股票")
        st.dataframe(df_result, use_container_width=True, hide_index=True)

        csv = df_result.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            label="下載選股結果 CSV",
            data=csv,
            file_name="策略選股結果.csv",
            mime="text/csv"
        )
    else:
        st.warning("今天沒有符合條件的股票")
else:
    st.info("按下『開始選股』後開始掃描。")
