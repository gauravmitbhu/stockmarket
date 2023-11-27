import streamlit as st
from GoogleNews import GoogleNews
import re
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

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

# Function to get NASDAQ Composite Index data and prepare the enhanced chart
def get_nasdaq_chart():
    # Fetching 20 years of NASDAQ data
    nasdaq = yf.Ticker("^IXIC")
    hist = nasdaq.history(period="20y")

    # Plotting the line chart
    plt.figure(figsize=(15, 8))
    plt.plot(hist.index, hist['Close'], color='blue', linewidth=1)

    # Defining a crash as a decrease of >10% within a week
    crash_threshold = -10  # Percentage
    window_size = 5  # Days

    # Identifying crashes
    hist['Percent Change'] = hist['Close'].pct_change().rolling(window=window_size).sum()
    crash_points = hist[hist['Percent Change'] <= crash_threshold]

    # Marking crash points on the chart
    plt.scatter(crash_points.index, crash_points['Close'], color='red', label='Crash Points')

    # Analyzing the last two days to predict the current trend
    last_two_days = hist['Percent Change'].tail(2).mean()
    if last_two_days > crash_threshold:
        current_trend = "Heading towards a crash"
    else:
        current_trend = "Market is stable"

    plt.title(f'NASDAQ Composite Index - 20 Years History\nCurrent Trend: {current_trend}')
    plt.xlabel('Year')
    plt.ylabel('Close Price')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    return plt

# Streamlit app layout
st.title("Stock Market Insights")

if st.button("Analyze Trend"):
    positive_count, negative_count, neutral_count, articles = get_stock_market_trend()

    st.write(f"Total articles fetched: {len(articles)}")
    st.write(f"Positive articles count: {positive_count}")
    st.write(f"Negative articles count: {negative_count}")
    st.write(f"Neutral articles count: {neutral_count}")

    for article, category in articles:
        st.write(f"**{article}** - *{category}*")

    if positive_count > negative_count and positive_count > neutral_count:
        st.subheader("Stock market trend is positive/up.")
    elif negative_count > positive_count and negative_count > neutral_count:
        st.subheader("Stock market trend is negative/down.")
    elif neutral_count > positive_count and neutral_count > negative_count:
        st.subheader("Stock market is stable.")
    else:
        st.subheader("Mixed or unclear stock market trend.")

if st.button("Show NASDAQ Chart"):
    nasdaq_chart = get_nasdaq_chart()
    st.pyplot(nasdaq_chart)
