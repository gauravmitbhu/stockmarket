import streamlit as st
from GoogleNews import GoogleNews
import re

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

# Streamlit app layout
st.title("Stock Market Trend Analysis")

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
