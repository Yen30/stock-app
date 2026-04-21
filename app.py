import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import urllib3
from io import StringIO

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="策略選股", page_icon="📈", layout="centered")

st.title("策略選股（全台股）")
st.write("條件：25MA上 + 5日均量金叉60日均量 + 成交量>5000")

# =====================
# 取得台股清單
# =====================
@st.cache_data(ttl=3600)
def get_twse():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    res = requests.get(url, headers={"User-Agent": "Mozilla"}, verify=False)
    res.encoding = "big5"

    df = pd.read_html(StringIO(res.text))[0]
    df.columns = df.iloc[0]
    df = df.iloc[1:]

    df = df[df["有價證券別"] == "股票"]
    df["代號"] = df["代號及名稱"].str.split("　").str[0]
    df = df[df["代號"].str.match(r"^\d{4}$", na=False)]

    return [x + ".TW" for x in df["代號"].tolist()]

@st.cache_data(ttl=3600)
def get_tpex():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
    res = requests.get(url, headers={"User-Agent": "Mozilla"}, verify=False)
    res.encoding = "big5"

    df = pd.read_html(StringIO(res.text))[0]
    df.columns = df.iloc[0]
    df = df.iloc[1:]

    df = df[df["有價證券別"] == "股票"]
    df["代號"] = df["代號及名稱"].str.split("　").str[0]
    df = df[df["代號"].str.match(r"^\d{4}$", na=False)]

    return [x + ".TWO" for x in df["代號"].tolist()]

@st.cache_data(ttl=3600)
def get_all():
    return get_twse() + get_tpex()

# =====================
# 抓資料
# =====================
def get_data(ticker):
    try:
        df = yf.download(ticker, period="8mo", progress=False, threads=False)
        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df.columns = [str(c).title() for c in df.columns]
        return df
    except:
        return None

# =====================
# 條件
# =====================
def check(df):
    if df is None or len(df) < 70:
        return None

    df["MA25"] = df["Close"].rolling(25).mean()
    df["VMA5"] = df["Volume"].rolling(5).mean()
    df["VMA60"] = df["Volume"].rolling(60).mean()

    prev = df.iloc[-2]
    last = df.iloc[-1]

    cond1 = last["Close"] > last["MA25"]

    cond2 = (
        prev["VMA5"] < prev["VMA60"] and
        last["VMA5"] > last["VMA60"]
    )

    cond3 = last["Volume"] > 5000

    if cond1 and cond2 and cond3:
        return {
            "股票": "",
            "收盤價": round(float(last["Close"]), 2),
            "25MA": round(float(last["MA25"]), 2),
            "成交量": int(last["Volume"])
        }

    return None

# =====================
# UI 選擇
# =====================
mode = st.selectbox(
    "掃描範圍",
    ["先掃 100 檔（最快）", "掃 300 檔", "全部台股（慢）"]
)

if mode == "先掃 100 檔（最快）":
    limit = 100
elif mode == "掃 300 檔":
    limit = 300
else:
    limit = None

# =====================
# 主執行
# =====================
if st.button("開始選股"):

    tickers = get_all()

    if limit:
        tickers = tickers[:limit]

    st.write(f"掃描 {len(tickers)} 檔股票")

    progress = st.progress(0)
    results = []

    for i, t in enumerate(tickers):
        df = get_data(t)
        r = check(df)

        if r:
            r["股票"] = t.replace(".TW", "").replace(".TWO", "")
            results.append(r)

        progress.progress((i + 1) / len(tickers))

    if results:
        df_result = pd.DataFrame(results)
        st.success(f"找到 {len(df_result)} 檔")
        st.dataframe(df_result)
    else:
        st.warning("今天沒有符合條件的股票")
