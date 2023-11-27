import streamlit as st
from GoogleNews import GoogleNews
import re
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime


# Function to get stock market trend
def get_stock_market_trend():
    googlenews = GoogleNews(lang='en', region='US')
    googlenews.search('stock market')
    result = googlenews.result()

    positive_keywords = r"\b(up|rise|gain|positive|bullish)\b"
    negative_keywords = r"\b(down|fall|drop|negative|bearish)\b"
    neutral_keywords = r"\b(stable|steady|unchanged|flat)\b"

    positive_count, negative_count, neutral_count = 0, 0, 0
    articles = []

    for item in result:
        title = item['title'].lower()
        category = "Unclassified"
        if re.search(positive_keywords, title):
            positive_count += 1
            category = "Positive"
        elif re.search(negative_keywords, title):
            negative_count += 1
            category = "Negative"
        elif re.search(neutral_keywords, title):
            category = "Neutral"
        articles.append((item['title'], category))

    return positive_count, negative_count, neutral_count, articles


# Function to calculate RSI
def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


# Function to calculate MACD
def calculate_macd(data, n_slow=26, n_fast=12, n_signal=9):
    ema_fast = data['Close'].ewm(span=n_fast, adjust=False).mean()
    ema_slow = data['Close'].ewm(span=n_slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=n_signal, adjust=False).mean()
    return macd_line, signal_line


# Function to get NASDAQ Composite Index data and prepare the enhanced chart
def get_nasdaq_chart(ticker_symbol, start_date=None, end_date=None, time_frame=None):
    ticker_data = yf.Ticker(ticker_symbol)
    if time_frame:
        end_date = datetime.now()
        start_date = end_date - pd.DateOffset(years=time_frame)
    hist = ticker_data.history(start=start_date, end=end_date)
    hist['RSI'] = calculate_rsi(hist)
    hist['MACD_Line'], hist['Signal_Line'] = calculate_macd(hist)
    plt.figure(figsize=(15, 8))
    plt.plot(hist.index, hist['Close'], color='blue', linewidth=1)
    major_crash_threshold = -9
    window_size = 5
    for i in range(window_size, len(hist)):
        window = hist.iloc[i - window_size:i]
        percent_change = (hist['Close'].iloc[i] - window['Close'].max()) / window['Close'].max() * 100
        if percent_change <= major_crash_threshold and 30 <= hist['RSI'].iloc[i] <= 40 and hist['MACD_Line'].iloc[i] < \
                hist['Signal_Line'].iloc[i]:
            plt.scatter(hist.index[i], hist['Close'].iloc[i], color='red',
                        label='Major Dip (RSI 30-40, MACD < Signal)' if 'Major Dip (RSI 30-40, MACD < Signal)' not in
                                                                          plt.gca().get_legend_handles_labels()[
                                                                              1] else '')
    plt.title(f'{ticker_symbol} - Custom Timeframe')
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    return plt


# Streamlit app layout
st.title("StockDips - Know when market is best to invest")

# Toggle for advanced mode
advanced_mode = st.checkbox("Toggle Advanced Mode")

# Ticker selection
ticker_options = {
    "NASDAQ Composite": "^IXIC",
    "Bitcoin": "BTC-USD",
    "NYSE Composite": "^NYA"
}
selected_ticker = st.selectbox("Select Ticker", list(ticker_options.keys()), disabled=not advanced_mode)
ticker_symbol = ticker_options[selected_ticker]

# Predefined Timeframe Selection
time_frame = st.selectbox("Select Predefined Timeframe", [1, 5, 10, 20], index=3, key='predefined_tf_selection')

# Show default 5-year graph and Substack subscription button if advanced mode is not enabled
if not advanced_mode:
    nasdaq_chart_default = get_nasdaq_chart(ticker_symbol, time_frame=5)
    st.pyplot(nasdaq_chart_default)

    # Button to subscribe to Substack
    substack_url = "https://yodatalks.substack.com/subscribe"
    st.markdown(
        f"<a href='{substack_url}' target='_blank'><button style='color: white; background-color: blue; padding: 10px 20px; border-radius: 5px; border: none; font-size: 16px;'>Subscribe to StockDips</button></a>",
        unsafe_allow_html=True)

# Display additional options if advanced mode is enabled
if advanced_mode:
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
