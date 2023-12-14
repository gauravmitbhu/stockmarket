import matplotlib.pyplot as plt
import yfinance as yf
from datetime import datetime
from data_analysis import calculate_rsi, calculate_macd
import pandas as pd

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
