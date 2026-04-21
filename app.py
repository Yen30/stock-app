import io
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from io import StringIO

st.set_page_config(page_title="策略選股", page_icon="📈", layout="wide")

CUSTOM_CSS = """
<style>
.block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
.stButton>button {width: 100%; height: 3rem; font-size: 1.05rem; border-radius: 12px;}
.metric-card {padding: 0.8rem 1rem; border: 1px solid #e5e7eb; border-radius: 14px; background: #ffffff;}
.small-note {color: #6b7280; font-size: 0.92rem;}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

DEFAULT_MAX_RESULTS = 10


def get_tw_stock_list(limit_mode: str = "測試模式"):
    """Get TWSE + TPEx common stock list. limit_mode: 測試模式 / 較完整模式 / 全市場"""
    urls = [
        "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2",  # listed
        "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4",  # OTC
    ]
    tickers = []

    for url in urls:
        try:
            res = requests.get(url, timeout=20)
            res.encoding = "big5-hkscs"
            tables = pd.read_html(StringIO(res.text))
            if not tables:
                continue
            df = tables[0]
            df.columns = df.iloc[0]
            df = df.iloc[1:].copy()
            df = df[df["有價證券別"] == "股票"]
            df = df[~df["代號及名稱"].astype(str).str.contains("特別股", na=False)]
            df["代號"] = df["代號及名稱"].astype(str).str.split("　").str[0]
            suffix = ".TW" if "strMode=2" in url else ".TWO"
            tickers.extend([f"{code}{suffix}" for code in df["代號"].tolist() if str(code).isdigit()])
        except Exception:
            continue

    tickers = list(dict.fromkeys(tickers))

    if limit_mode == "測試模式":
        return tickers[:40]
    if limit_mode == "較完整模式":
        return tickers[:300]
    return tickers


def download_data(ticker: str, period: str = "8mo"):
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=False, threads=False)
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df.columns = [str(c).title() for c in df.columns]
        return df
    except Exception:
        return None


def add_indicators(df: pd.DataFrame):
    df = df.copy()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["Prev20High"] = df["High"].shift(1).rolling(20).max()
    df["Low10"] = df["Low"].rolling(10).min()
    df["VMA10"] = df["Volume"].rolling(10).mean()
    df["VMA60"] = df["Volume"].rolling(60).mean()
    df["PctChange"] = df["Close"].pct_change() * 100
    return df


def evaluate_signal(ticker: str, df: pd.DataFrame, min_volume_shares: int = 800_000):
    if df is None or len(df) < 70:
        return None, None

    df = add_indicators(df)
    prev = df.iloc[-2]
    last = df.iloc[-1]

    required = [prev["MA25"], last["MA25"], prev["VMA10"], prev["VMA60"], last["VMA10"], last["VMA60"], last["Prev20High"]]
    if any(pd.isna(x) for x in required):
        return None, None

    cond_break_25ma = prev["Close"] <= prev["MA25"] and last["Close"] > last["MA25"]
    cond_vol_cross = prev["VMA10"] <= prev["VMA60"] and last["VMA10"] > last["VMA60"]
    cond_liquidity = last["Volume"] >= min_volume_shares
    cond_strong_close = last["Close"] >= last["High"] * 0.95
    cond_volume_expand = last["Volume"] > prev["Volume"]
    cond_break_20h = last["High"] > last["Prev20High"]

    common = cond_break_25ma and cond_vol_cross and cond_liquidity

    base = {
        "日期": str(last.name.date()),
        "代號": ticker.replace(".TW", "").replace(".TWO", ""),
        "收盤價": round(float(last["Close"]), 2),
        "25MA": round(float(last["MA25"]), 2),
        "10均量": int(last["VMA10"]),
        "60均量": int(last["VMA60"]),
        "成交量": int(last["Volume"]),
        "漲跌幅%": round(float(last["PctChange"]), 2),
        "10日低點": round(float(last["Low10"]), 2),
        "前20日高點": round(float(last["Prev20High"]), 2),
        "收盤接近高點": "是" if cond_strong_close else "否",
        "量增": "是" if cond_volume_expand else "否",
    }

    trial = None
    add = None

    if common and cond_strong_close and cond_volume_expand:
        trial = base.copy()

    if common and cond_break_20h and cond_strong_close and cond_volume_expand:
        add = base.copy()
        add["今日最高"] = round(float(last["High"]), 2)

    return trial, add


@st.cache_data(ttl=3600, show_spinner=False)
def run_screener(limit_mode: str, max_results: int):
    tickers = get_tw_stock_list(limit_mode)
    trial_rows = []
    add_rows = []
    checked = 0

    for ticker in tickers:
        df = download_data(ticker)
        checked += 1
        trial, add = evaluate_signal(ticker, df)
        if trial:
            trial_rows.append(trial)
        if add:
            add_rows.append(add)

    trial_df = pd.DataFrame(trial_rows)
    add_df = pd.DataFrame(add_rows)

    if not trial_df.empty:
        trial_df = trial_df.sort_values(["漲跌幅%", "成交量"], ascending=[False, False]).head(max_results).reset_index(drop=True)
    if not add_df.empty:
        add_df = add_df.sort_values(["漲跌幅%", "成交量"], ascending=[False, False]).head(max_results).reset_index(drop=True)

    return trial_df, add_df, checked, len(tickers)


def df_to_csv_bytes(df: pd.DataFrame):
    return df.to_csv(index=False).encode("utf-8-sig")


st.title("策略選股")
st.caption("條件：突破 25 日均線、10 日均量線金叉 60 日均量線；分成試單名單與加碼名單，各顯示 10 檔。")

with st.container():
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("掃描範圍", ["測試模式", "較完整模式", "全市場"], index=0)
    with col2:
        st.markdown('<div class="metric-card"><b>顯示上限</b><br>試單 10 檔 / 加碼 10 檔</div>', unsafe_allow_html=True)

st.markdown('<div class="small-note">建議先用測試模式確認可正常執行，再切換到較完整模式或全市場。</div>', unsafe_allow_html=True)

if st.button("開始選股", type="primary"):
    with st.spinner("正在抓取股價資料並計算訊號，請稍候…"):
        trial_df, add_df, checked, total = run_screener(mode, DEFAULT_MAX_RESULTS)

    c1, c2, c3 = st.columns(3)
    c1.metric("掃描股票數", f"{checked}/{total}")
    c2.metric("試單名單", len(trial_df))
    c3.metric("加碼名單", len(add_df))

    st.subheader("試單名單")
    st.write("條件：突破 25MA + 10/60 均量黃金交叉 + 量增 + 收盤偏強")
    if trial_df.empty:
        st.info("今天沒有符合試單條件的股票。")
    else:
        st.dataframe(trial_df, use_container_width=True, hide_index=True)
        st.download_button(
            "下載試單名單 CSV",
            data=df_to_csv_bytes(trial_df),
            file_name=f"trial_list_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.subheader("加碼名單")
    st.write("條件：試單條件成立，且今日再突破前 20 日高點")
    if add_df.empty:
        st.info("今天沒有符合加碼條件的股票。")
    else:
        st.dataframe(add_df, use_container_width=True, hide_index=True)
        st.download_button(
            "下載加碼名單 CSV",
            data=df_to_csv_bytes(add_df),
            file_name=f"add_list_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            use_container_width=True,
        )

else:
    st.info("按下『開始選股』後就會開始掃描。")
    st.markdown(
        """
        - **試單名單**：突破 25MA、10 日均量金叉 60 日均量、量增、收盤偏強。
        - **加碼名單**：在試單基礎上，再突破前 20 日高點。
        - **停損參考**：表格內會帶出 10 日低點。
        """
    )
