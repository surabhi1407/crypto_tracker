import streamlit as st
import requests
import pandas as pd
import altair as alt
from datetime import datetime

st.set_page_config(page_title="Bitcoin Market Signals", layout="wide")

st.title("📊 Bitcoin Market Signals Dashboard")

# # ----- Define tabs -----
# tab1, tab2, tab3, tab4, tab5 = st.tabs(
#     ["📝 Notes", "💰 Price Trend", "🏦 ETF Inflows", "🔗 On-Chain Health", "😌 Sentiment Gauge"]
# )
# ----- Define tabs -----
tab2, = st.tabs([
    "💰 Price Trend"
])

# # ===== Tab 1: Empty (for user notes) =====
# with tab1:
#     st.subheader("Your Notes / Future Section")
#     st.text_area("Write here...", placeholder="You can add your strategy notes or calculations.")
# ===== Tab 2: Price Trend (with Slider + Robust API Handling) =====
with tab2:
    st.subheader("Bitcoin Price (MYR) — Volatility Zones + Insights")

    # --- Fetch data safely ---
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=myr&days=365"
    r = requests.get(url)

    if r.status_code != 200:
        st.error(f"CoinGecko API error: {r.status_code}")
        st.stop()

    data = r.json()

    if "prices" not in data:
        st.error("API response did not contain 'prices' data. Please try again in a few minutes.")
        st.json(data)  # show what was returned for debugging
        st.stop()

    # --- Continue processing if data OK ---
    prices = pd.DataFrame(data["prices"], columns=["timestamp", "myr"])
    prices["timestamp"] = pd.to_datetime(prices["timestamp"], unit="ms")
    prices.rename(columns={"myr": "MYR"}, inplace=True)
    prices["daily_change"] = prices["MYR"].pct_change() * 100
    prices["volatility_7d"] = prices["daily_change"].rolling(7).std()

    # --- Time slider ---
    total_days = (prices["timestamp"].max() - prices["timestamp"].min()).days
    total_months = int(total_days / 30)
    step = 2
    months_back = st.slider(
        "⏱️ Select Look-Back Period (months)",
        min_value=2,
        max_value=min(total_months, 12),
        value=6,
        step=step
    )

    # --- Filter data by look-back period ---
    end_date = prices["timestamp"].max()
    start_date = end_date - pd.DateOffset(months=months_back)
    filtered = prices[prices["timestamp"] >= start_date]

    # --- Volatility classification ---
    def classify_zone(v):
        if v < 0.3: return "🟩 Calm"
        elif v < 0.8: return "🟨 Moderate"
        else: return "🟥 High Risk"

    latest = filtered.iloc[-1]
    current_price = latest["MYR"]
    current_vol = classify_zone(latest["volatility_7d"])

    last_30 = filtered.tail(30)
    trend = "📈 Uptrend" if last_30["MYR"].iloc[-1] > last_30["MYR"].iloc[0] else \
             "📉 Downtrend" if last_30["MYR"].iloc[-1] < last_30["MYR"].iloc[0] else "➡️ Sideways"

    # --- Metrics row ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Market Volatility", current_vol)
    col2.metric("BTC Price", f"RM {current_price:,.0f}")
    col3.metric("30-Day Trend", trend)

    # --- Interpretation ---
    with st.expander("💡 How to interpret volatility based on your time range"):
        st.write(f"""
        You’re currently viewing **the last {months_back} months** of data.

        **Shorter windows (2–4 months)** → reacts quickly; shows trader-style noise.  
        **Medium windows (4–8 months)** → balanced view; shows real trend direction.  
        **Longer windows (8–12 months)** → smooths out spikes; suited for long-term view.  

        - 🟩 Calm → steadier phase; good for accumulating.  
        - 🟨 Moderate → typical BTC movement; DCA works.  
        - 🟥 High → turbulent market; best to wait or buy gradually.
        """)

    # --- Chart (MYR) ---
    filtered["vol_zone"] = filtered["volatility_7d"].apply(classify_zone)
    color_scale = alt.Scale(
        domain=["🟩 Calm", "🟨 Moderate", "🟥 High Risk"],
        range=["#2ecc71", "#f1c40f", "#e74c3c"]
    )
    base = alt.Chart(filtered).encode(x="timestamp:T")
    background = base.mark_area(opacity=0.3).encode(
        y=alt.Y("MYR:Q", title="Price (RM)"),
        color=alt.Color("vol_zone:N", scale=color_scale,
                        legend=alt.Legend(title="Volatility Zone"))
    )
    price_line = base.mark_line(color="black", strokeWidth=2).encode(y="MYR:Q")
    st.altair_chart((background + price_line).properties(height=400),
                    use_container_width=True)

    st.caption("🟩 Calm • 🟨 Moderate • 🟥 High Risk — Source: CoinGecko API (MYR feed)")
