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

strategy = st.selectbox(
    "選擇策略",
    ["策略1：突破股", "策略2：轉強起漲股"]
)


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


def _extract_codes_with_filter(df: pd.DataFrame, suffix: str) -> list[str]:
    if df.empty:
        return []

    first_col = df.columns[0]

    industry_col = None
    for col in df.columns:
        if "產業" in col:
            industry_col = col
            break

    codes = []

    for i, val in enumerate(df[first_col].astype(str)):
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

        codes.append(f"{code}{suffix}")

    return sorted(list(set(codes)))


@st.cache_data(ttl=3600)
def get_all_tickers():
    df1 = _fetch_isin_table(2)
    df2 = _fetch_isin_table(4)
    return sorted(list(set(
        _extract_codes_with_filter(df1, ".TW") +
        _extract_codes_with_filter(df2, ".TWO")
    )))


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
# 策略1：突破股
# =========================
def check_strategy1(df):
    if df is None or len(df) < 130:
        return None

    df = df.copy()

    df["MA25"] = df["Close"].rolling(25).mean()
    df["MA44"] = df["Close"].rolling(44).mean()
    df["MA44_prev"] = df["MA44"].shift(1)

    df["Volume張"] = df["Volume"] / 1000
    df["VMA5"] = df["Volume張"].rolling(5).mean()
    df["VMA120"] = df["Volume張"].rolling(120).mean()

    last = df.iloc[-1]

    cond_price = last["Close"] > last["MA44"]
    cond_ma_up = last["MA44"] > last["MA44_prev"]
    cond_ma_structure = last["MA25"] > last["MA44"]
    cond_volume = last["VMA5"] > last["VMA120"]
    cond_liquidity = last["Volume張"] > 5000
    cond_break = last["Close"] >= df["Close"].rolling(20).max().iloc[-2] * 1.02
    cond_not_too_far = last["Close"] / last["MA25"] < 1.2

    if (
        cond_price and
        cond_ma_up and
        cond_ma_structure and
        cond_volume and
        cond_liquidity and
        cond_break and
        cond_not_too_far
    ):
        return {
            "股票": "",
            "收盤價": round(float(last["Close"]), 2),
            "25日線": round(float(last["MA25"]), 2),
            "44日線": round(float(last["MA44"]), 2),
            "乖離": round(float(last["Close"] / last["MA25"]), 2),
            "成交量(張)": int(last["Volume張"]),
        }

    return None


# =========================
# 策略2：轉強起漲股
# =========================
def check_strategy2(df):
    if df is None or len(df) < 100:
        return None

    df = df.copy()

    df["MA44"] = df["Close"].rolling(44).mean()
    df["Volume張"] = df["Volume"] / 1000
    df["VMA5"] = df["Volume張"].rolling(5).mean()

    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = df["EMA12"] - df["EMA26"]
    df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["MACD"] = df["DIF"] - df["DEA"]

    prev = df.iloc[-2]
    last = df.iloc[-1]
    ma44_3days_ago = df["MA44"].iloc[-4]

    # 1. 昨天收盤 < 昨天44MA，今天收盤 > 今天44MA
    cond_cross_44ma = (
        pd.notna(prev["MA44"]) and
        pd.notna(last["MA44"]) and
        prev["Close"] < prev["MA44"] and
        last["Close"] > last["MA44"]
    )

    # 2. 今天44MA > 3天前44MA
    cond_ma44_turn_up = (
        pd.notna(ma44_3days_ago) and
        last["MA44"] > ma44_3days_ago
    )

    # 3. 收盤價 / 44MA < 1.1
    cond_not_too_far = (
        pd.notna(last["MA44"]) and
        last["Close"] / last["MA44"] < 1.1
    )

    # 4. 今日成交量 > 5日均量
    cond_volume_up = (
        pd.notna(last["VMA5"]) and
        last["Volume張"] > last["VMA5"]
    )

    # 5. DIF 昨天 < 0，今天 DIF > 0
    cond_dif_cross_zero = (
        pd.notna(prev["DIF"]) and
        pd.notna(last["DIF"]) and
        prev["DIF"] < 0 and
        last["DIF"] > 0
    )

    if (
        cond_cross_44ma and
        cond_ma44_turn_up and
        cond_not_too_far and
        cond_volume_up and
        cond_dif_cross_zero
    ):
        return {
            "股票": "",
            "收盤價": round(float(last["Close"]), 2),
            "44日線": round(float(last["MA44"]), 2),
            "44MA乖離": round(float(last["Close"] / last["MA44"]), 2),
            "DIF": round(float(last["DIF"]), 2),
            "MACD": round(float(last["MACD"]), 2),
            "成交量(張)": int(last["Volume張"]),
            "5日均量(張)": int(last["VMA5"]),
        }

    return None


if st.button("開始選股"):
    tickers = get_all_tickers()

    st.write(f"掃描 {len(tickers)} 檔股票（已排除特定產業）")

    progress = st.progress(0)
    results = []

    for i, ticker in enumerate(tickers):
        df = get_data(ticker)

        if strategy == "策略1：突破股":
            result = check_strategy1(df)
        else:
            result = check_strategy2(df)

        if result:
            result["股票"] = ticker.replace(".TW", "").replace(".TWO", "")
            results.append(result)

        progress.progress((i + 1) / len(tickers))

    if results:
        df_result = pd.DataFrame(results)

        if "成交量(張)" in df_result.columns:
            df_result = df_result.sort_values(by="成交量(張)", ascending=False)

        df_result = df_result.reset_index(drop=True)

        st.success(f"找到 {len(df_result)} 檔")
        st.dataframe(df_result, use_container_width=True, hide_index=True)
    else:
        st.warning("今天沒有符合條件的股票")
else:
    st.info("選擇策略後，按下『開始選股』")
