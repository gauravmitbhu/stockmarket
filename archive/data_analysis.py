import re
from GoogleNews import GoogleNews

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

