import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="策略選股🔥", page_icon="🔥", layout="centered")
st.title("策略選股（5策略＋強度排名🔥）")


# =========================
# 固定股票池
# =========================
@st.cache_data(ttl=3600)
def get_all_tickers():
    return [
        "1101.TW","1102.TW","1301.TW","1303.TW","1326.TW",
        "1402.TW","1477.TW","1503.TW","1513.TW","1514.TW",
        "1515.TW","1519.TW","1522.TW","1536.TW","1560.TW",
        "1590.TW","1605.TW","1707.TW","1717.TW","1722.TW",
        "1802.TW","1904.TW","1907.TW","2002.TW","2006.TW",
        "2014.TW","2027.TW","2031.TW","2105.TW","2201.TW",
        "2204.TW","2206.TW","2207.TW","2301.TW","2303.TW",
        "2308.TW","2312.TW","2313.TW","2314.TW","2316.TW",
        "2317.TW","2324.TW","2327.TW","2328.TW","2329.TW",
        "2330.TW","2337.TW","2338.TW","2344.TW","2345.TW",
        "2347.TW","2351.TW","2352.TW","2353.TW","2354.TW",
        "2356.TW","2357.TW","2359.TW","2360.TW","2362.TW",
        "2363.TW","2364.TW","2365.TW","2367.TW","2368.TW",
        "2371.TW","2373.TW","2374.TW","2375.TW","2376.TW",
        "2377.TW","2379.TW","2382.TW","2383.TW","2385.TW",
        "2387.TW","2388.TW","2392.TW","2393.TW","2395.TW",
        "2401.TW","2402.TW","2404.TW","2405.TW","2408.TW",
        "2409.TW","2412.TW","2413.TW","2414.TW","2415.TW",
        "2417.TW","2421.TW","2423.TW","2425.TW","2426.TW",
        "2427.TW","2428.TW","2429.TW","2430.TW","2431.TW",
        "2436.TW","2439.TW","2441.TW","2442.TW","2448.TW",
        "2449.TW","2450.TW","2451.TW","2453.TW","2454.TW",
        "2455.TW","2457.TW","2458.TW","2460.TW","2461.TW",
        "2462.TW","2464.TW","2465.TW","2467.TW","2471.TW",
        "2472.TW","2474.TW","2476.TW","2477.TW","2478.TW",
        "2480.TW","2481.TW","2482.TW","2483.TW","2484.TW",
        "2485.TW","2486.TW","2488.TW","2489.TW","2491.TW",
        "2492.TW","2493.TW","2495.TW","2497.TW","2498.TW",
        "3003.TW","3005.TW","3006.TW","3008.TW","3010.TW",
        "3013.TW","3014.TW","3015.TW","3016.TW","3017.TW",
        "3019.TW","3022.TW","3023.TW","3024.TW","3025.TW",
        "3026.TW","3027.TW","3028.TW","3029.TW","3030.TW",
        "3031.TW","3032.TW","3033.TW","3034.TW","3035.TW",
        "3036.TW","3037.TW","3038.TW","3041.TW","3042.TW",
        "3043.TW","3044.TW","3045.TW","3046.TW","3047.TW",
        "3048.TW","3049.TW","3050.TW","3051.TW","3052.TW",
        "3054.TW","3055.TW","3056.TW","3057.TW","3058.TW",
        "3059.TW","3060.TW","3090.TW","3189.TW","3209.TW",
        "3231.TW","3257.TW","3266.TW","3296.TW","3305.TW",
        "3311.TW","3321.TW","3338.TW","3376.TW","3380.TW",
        "3406.TW","3413.TW","3443.TW","3450.TW","3481.TW",
        "3532.TW","3533.TW","3535.TW","3545.TW","3550.TW",
        "3563.TW","3576.TW","3592.TW","3653.TW","3661.TW",
        "3673.TW","3682.TW","3702.TW","3706.TW","3707.TW",
        "3711.TW","3715.TW","4915.TW","4919.TW","4938.TW",
        "4958.TW","4961.TW","4966.TW","4994.TW","5269.TW",
        "5434.TW","5469.TWO","5483.TWO","5608.TW","6116.TW",
        "6121.TWO","6139.TW","6153.TW","6176.TW","6183.TW",
        "6213.TW","6239.TW","6257.TW","6271.TW","6274.TW",
        "6285.TW","6415.TW","6438.TW","6443.TW","6472.TW",
        "6515.TW","6531.TW","6533.TW","6669.TW","6691.TW",
        "6719.TW","6781.TW","6805.TW","8016.TW","8046.TW",
        "8112.TW","8150.TW","8210.TW","8215.TW","8249.TW",
        "8261.TW","8299.TW","8358.TW","8996.TW","9904.TW",
        "9910.TW","9914.TW","9921.TW","9941.TW","9958.TW",
        "2603.TW","2605.TW","2606.TW","2609.TW","2610.TW",
        "2615.TW","2618.TW","2630.TW","2633.TW","2634.TW",
        "2636.TW","2637.TW","2645.TW","2646.TW",
    ]


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
    if df is None or len(df) < 70:
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
    if df is None or len(df) < 70:
        return False

    df = df.copy()
    df["MA44"] = df["Close"].rolling(44).mean()

    df["V"] = df["Volume"] / 1000

    df["EMA12"] = df["Close"].ewm(span=12, adjust=False).mean()
    df["EMA26"] = df["Close"].ewm(span=26, adjust=False).mean()
    df["DIF"] = df["EMA12"] - df["EMA26"]
    df["DEA"] = df["DIF"].ewm(span=9, adjust=False).mean()
    df["OSC"] = df["DIF"] - df["DEA"]

    prev = df.iloc[-2]
    last = df.iloc[-1]

    return (
        last["OSC"] < 1 and
        last["OSC"] > prev["OSC"] and
        prev["Close"] < prev["MA44"] and
        last["Close"] > last["MA44"] and
        last["Close"] > prev["Close"] and
        last["V"] > 3000
    )


def s5(df):
    if df is None or len(df) < 120:
        return False

    df = df.copy()

    df_w = df.resample("W").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum"
    }).dropna()

    if len(df_w) < 25:
        return False

    df_w["V"] = df_w["Volume"] / 1000
    df_w["V5"] = df_w["V"].rolling(5).mean()
    df_w["MA22"] = df_w["Close"].rolling(22).mean()

    prev = df_w.iloc[-2]
    last = df_w.iloc[-1]

    return (
        last["V"] < last["V5"] and
        last["Close"] > prev["Close"] and
        last["Close"] > last["MA22"]
    )


if st.button("開始掃描🔥"):
    tickers = get_all_tickers()
    results = []

    progress = st.progress(0)

    for i, ticker in enumerate(tickers):
        df = get_data(ticker)

        if df is None:
            progress.progress((i + 1) / len(tickers))
            continue

        code = ticker.replace(".TW", "").replace(".TWO", "")

        hit1 = s1(df)
        hit2 = s2(df)
        hit3 = s3(df)
        hit4 = s4(df)
        hit5 = s5(df)

        score = int(hit1) + int(hit2) + int(hit3) + int(hit4) + int(hit5)

        if score > 0:
            results.append({
                "股票": code,
                "強度": score,
                "策略1": "✅" if hit1 else "",
                "策略2": "✅" if hit2 else "",
                "策略3": "✅" if hit3 else "",
                "策略4": "👀" if hit4 else "",
                "策略5週K": "🌀" if hit5 else "",
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
