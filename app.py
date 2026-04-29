import re
from io import StringIO

import pandas as pd
import requests
import streamlit as st
import urllib3
import yfinance as yf

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="策略選股🔥", page_icon="🔥", layout="centered")
st.title("策略選股（4策略＋強度排名🔥）")


def _fetch_isin_table(str_mode: int):
    url = f"https://isin.twse.com.tw/isin/C_public.jsp?strMode={str_mode}"
    res = requests.get(url, timeout=20, verify=False)
    res.encoding = "big5"
    df = pd.read_html(StringIO(res.text))[0]
    df.columns = df.iloc[0]
    return df.iloc[1:]


def _extract_codes(df, suffix):
    codes = []

    industry_col = None
    for col in df.columns:
        if "產業" in str(col):
            industry_col = col
            break

    for i, val in enumerate(df.iloc[:, 0].astype(str)):
        m = re.match(r"^(\d{4})", val)
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
    return list(set(
        _extract_codes(_fetch_isin_table(2), ".TW") +
        _extract_codes(_fetch_isin_table(4), ".TWO")
    ))


def get_data(t):
    try:
        df = yf.download(t, period="1y", progress=False, auto_adjust=False)

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        df.columns = [str(c).title() for c in df.columns]
        return df
    except:
        return None


def s1(df):
    if len(df) < 130:
        return False

    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA44"] = df["Close"].rolling(44).mean()

    df["V"] = df["Volume"] / 1000
    df["V5"] = df["V"].rolling(5).mean()
    df["V120"] = df["V"].rolling(120).mean()

    last = df.iloc[-1]
    prev60 = df["Close"].shift(1).rolling(60).max().iloc[-1]

    return (
        last["Close"] > last["MA44"] and
        last["MA44"] > df["MA44"].iloc[-2] and
        last["MA25"] > last["MA44"] and
        last["V5"] > last["V120"] and
        last["V"] > 5000 and
        last["Close"] > prev60 and
        last["Close"] / last["MA25"] < 1.12 and
        last["Close"] > last["MA5"]
    )


def s2(df):
    if len(df) < 100:
        return False

    df = df.copy()
    df["MA44"] = df["Close"].rolling(44).mean()
    df["V"] = df["Volume"] / 1000
    df["V5"] = df["V"].rolling(5).mean()

    df["EMA12"] = df["Close"].ewm(span=12).mean()
    df["EMA26"] = df["Close"].ewm(span=26).mean()
    df["DIF"] = df["EMA12"] - df["EMA26"]

    prev = df.iloc[-2]
    last = df.iloc[-1]

    return (
        prev["Close"] < prev["MA44"] and
        last["Close"] > last["MA44"] and
        last["MA44"] > df["MA44"].iloc[-6] and
        last["Close"] / last["MA44"] < 1.1 and
        last["V"] > last["V5"] and
        last["V"] > prev["V"] and
        prev["DIF"] < 0 and
        last["DIF"] > 0
    )


def s3(df):
    if len(df) < 70:
        return False

    df = df.copy()
    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA44"] = df["Close"].rolling(44).mean()

    df["V"] = df["Volume"] / 1000
    df["V5"] = df["V"].rolling(5).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]

    high20 = df["Close"].shift(1).rolling(20).max().iloc[-1]
    hi = df["High"].shift(1).rolling(20).max().iloc[-1]
    lo = df["Low"].shift(1).rolling(20).min().iloc[-1]

    box = (hi - lo) / lo

    return (
        last["Close"] > high20 * 1.03 and
        box < 0.15 and
        last["V"] > last["V5"] * 1.5 and
        prev["V"] < prev["V5"] and
        last["MA44"] > df["MA44"].iloc[-4] and
        last["Close"] / last["MA25"] < 1.15
    )


def s4(df):
    if len(df) < 70:
        return False

    df = df.copy()
    df["MA5"] = df["Close"].rolling(5).mean()
    df["MA44"] = df["Close"].rolling(44).mean()

    df["V"] = df["Volume"] / 1000

    df["EMA12"] = df["Close"].ewm(span=12).mean()
    df["EMA26"] = df["Close"].ewm(span=26).mean()
    df["DIF"] = df["EMA12"] - df["EMA26"]
    df["DEA"] = df["DIF"].ewm(span=9).mean()
    df["OSC"] = df["DIF"] - df["DEA"]

    prev = df.iloc[-2]
    last = df.iloc[-1]

    return (
        prev["OSC"] < 0 and
        last["OSC"] > 0 and
        last["MA5"] > last["MA44"] and
        last["Close"] > last["MA44"] and
        last["Close"] > prev["Close"] and
        last["V"] > 5000
    )


if st.button("開始掃描🔥"):
    tickers = get_all_tickers()
    results = []

    progress = st.progress(0)

    for i, t in enumerate(tickers):
        df = get_data(t)
        if df is None:
            progress.progress((i + 1) / len(tickers))
            continue

        code = t.replace(".TW", "").replace(".TWO", "")

        hit1 = s1(df)
        hit2 = s2(df)
        hit3 = s3(df)
        hit4 = s4(df)

        score = int(hit1) + int(hit2) + int(hit3) + int(hit4)

        if score > 0:
            results.append({
                "股票": code,
                "強度": score,
                "策略1": "✅" if hit1 else "",
                "策略2": "✅" if hit2 else "",
                "策略3": "✅" if hit3 else "",
                "策略4": "👀" if hit4 else "",
            })

        progress.progress((i + 1) / len(tickers))

    if results:
        df_result = pd.DataFrame(results)
        df_result = df_result.sort_values(by="強度", ascending=False).reset_index(drop=True)

        st.success(f"找到 {len(df_result)} 檔")
        st.dataframe(df_result, use_container_width=True, hide_index=True)
    else:
        st.warning("沒有符合條件的股票")
