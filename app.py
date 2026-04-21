import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import urllib3
from io import StringIO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="策略選股", page_icon="📈", layout="centered")

st.title("策略選股（全台股）")
st.write("條件：股價在25日均線上 + 5日均量線黃金交叉60日均量線 + 成交量大於5000")


@st.cache_data(ttl=3600)
def get_twse_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers, timeout=20, verify=False)
    res.encoding = "big5"

    tables = pd.read_html(StringIO(res.text))
    if not tables:
        return []

    df = tables[0]
    df.columns = df.iloc[0]
    df = df.iloc[1:]

    if "有價證券別" not in df.columns or "代號及名稱" not in df.columns:
        return []

    df = df[df["有價證券別"] == "股票"].copy()
    df = df.dropna(subset=["代號及名稱"])
    df["代號"] = df["代號及名稱"].astype(str).str.split("　").str[0]
    df = df[df["代號"].str.match(r"^\d{4}$", na=False)]

    return [f"{code}.TW" for code in df["代號"].tolist()]


@st.cache_data(ttl=3600)
def get_tpex_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    headers = {"User-Agent": "Mozilla/5.0"}

    res = requests.get(url, headers=headers, timeout=20, verify=False)
    res.encoding = "big5"

    tables = pd.read_html(StringIO(res.text))
    if not tables:
        return []

    df = tables[0]
    df.columns = df.iloc[0]
    df = df.iloc[1:]

    if "有價證券別" not in df.columns or "代號及名稱" not in df.columns:
        return []

    df = df[df["有價證券別"] == "股票"].copy()
    df = df.dropna(subset=["代號及名稱"])
    df["代號"] = df["代號及名稱"].astype(str).str.split("　").str[0]
    df = df[df["代號"].str.match(r"^\d{4}$", na=False)]

    return [f"{code}.TWO" for code in df["代號"].tolist()]


@st.cache_data(ttl=3600)
def get_all_tickers():
    twse = get_twse_tickers()
    tpex = get_tpex_tickers()
    tickers = twse + tpex
    return sorted(list(set(tickers)))


def get_data(ticker):
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
    df["VMA5"] = df["Volume"].rolling(5).mean()
    df["VMA60"] = df["Volume"].rolling(60).mean()

    prev = df.iloc[-2]
    last = df.iloc[-1]

    cond_price_above = (
        pd.notna(last["MA25"]) and
        last["Close"] > last["MA25"]
    )

    cond_volume_cross = (
        pd.notna(prev["VMA5"]) and
        pd.notna(prev["VMA60"]) and
        pd.notna(last["VMA5"]) and
        pd.notna(last["VMA60"]) and
        prev["VMA5"] < prev["VMA60"] and
        last["VMA5"] > last["VMA60"]
    )

    cond_liquidity = pd.notna(last["Volume"]) and last["Volume"] > 5000

    if cond_price_above and cond_volume_cross and cond_liquidity:
        return {
            "股票": "",
            "收盤價": round(float(last["Close"]), 2),
            "25日均線": round(float(last["MA25"]), 2),
            "成交量": int(last["Volume"]),
            "5日均量": int(last["VMA5"]),
            "60日均量": int(last["VMA60"]),
        }

    return None


scan_limit = st.selectbox(
    "掃描範圍",
    ["先掃 300 檔（較快）", "先掃 800 檔", "全部台股（較慢）"],
    index=0
)

if scan_limit == "先掃 300 檔（較快）":
    limit = 300
elif scan_limit == "先掃 800 檔":
    limit = 800
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
        df_result = df_result[["股票", "收盤價", "25日均線", "成交量", "5日均量", "60日均量"]]
        df_result = df_result.sort_values(by="成交量", ascending=False).reset_index(drop=True)

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
