import streamlit as st
from datetime import datetime
import chart_generation as cg
from data_analysis import get_stock_market_trend
from chart_generation import get_nasdaq_chart

st.title("StockDips - Know when market is best to invest")

advanced_mode = st.checkbox("Toggle Advanced Mode")

ticker_options = {
    "NASDAQ Composite": "^IXIC",
    "Bitcoin": "BTC-USD",
    "NYSE Composite": "^NYA"
}
selected_ticker = st.selectbox("Select Ticker", list(ticker_options.keys()), disabled=not advanced_mode)
ticker_symbol = ticker_options[selected_ticker]

time_frame = st.selectbox("Select Predefined Timeframe", [1, 5, 10, 20], index=3, key='predefined_tf_selection')

if not advanced_mode:
    nasdaq_chart_default = cg.get_nasdaq_chart(ticker_symbol, time_frame=5)
    st.pyplot(nasdaq_chart_default)

    substack_url = "https://yodatalks.substack.com/subscribe"
    st.markdown(f"<a href='{substack_url}' target='_blank'>...</a>", unsafe_allow_html=True)

if advanced_mode:
    # ... (rest of your advanced mode logic) ...

    if st.button("Analyze Trend", key="analyze_trend"):
        positive_count, negative_count, neutral_count, articles = get_stock_market_trend()
        st.write(f"Total articles fetched: {len(articles)}")
        st.write(f"Positive articles count: {positive_count}")
        st.write(f"Negative articles count: {negative_count}")
        st.write(f"Neutral articles count: {neutral_count}")
        for article, category in articles:
            st.write(f"**{article}** - *{category}*")

    if st.button("Show NASDAQ Chart for Predefined Timeframe", key="show_predefined_chart"):
        nasdaq_chart_predefined = get_nasdaq_chart(ticker_symbol, time_frame=time_frame)
        st.pyplot(nasdaq_chart_predefined)

    start_date = st.date_input("Start Date", datetime(2020, 1, 1), key="start_date")
    end_date = st.date_input("End Date", datetime.now(), key="end_date")
    if st.button("Show NASDAQ Chart for Custom Timeframe", key="show_custom_chart"):
        nasdaq_chart_custom = get_nasdaq_chart(ticker_symbol, start_date=start_date, end_date=end_date)
        st.pyplot(nasdaq_chart_custom)
