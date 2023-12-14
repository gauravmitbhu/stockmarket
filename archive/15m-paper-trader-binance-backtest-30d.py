import pandas as pd
from binance.client import Client
from datetime import datetime, timedelta

# Replace 'your_api_key' and 'your_api_secret' with your Binance API credentials
api_key = 'your_api_key'
api_secret = 'your_api_secret'
client = Client(api_key, api_secret)

symbol = 'BTCUSDT'
interval = '15m'
lookback = '3 months ago UTC'


# Function to fetch historical data from Binance
def fetch_historical_data(symbol, interval, lookback):
    klines = client.get_historical_klines(symbol, interval, lookback)
    # Create a DataFrame from the klines
    data = pd.DataFrame(klines, columns=[
        'Timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close_time',
        'Quote_asset_volume', 'Number_of_trades', 'Taker_buy_base_asset_volume',
        'Taker_buy_quote_asset_volume', 'Ignore'
    ])
    # Convert Timestamp to datetime and set it as index
    data['Timestamp'] = pd.to_datetime(data['Timestamp'], unit='ms')
    data.set_index('Timestamp', inplace=True)
    # Convert columns to appropriate data types
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        data[col] = pd.to_numeric(data[col], errors='coerce')
    return data


# Function to calculate RSI
def compute_rsi(data, window=14):
    delta = data['Close'].diff()
    up, down = delta.clip(lower=0), -delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    data['RSI'] = rsi
    return data


# Function to calculate MACD
def calculate_macd(data, fast_period=12, slow_period=26, signal_period=9):
    fast_ema = data['Close'].ewm(span=fast_period, min_periods=fast_period).mean()
    slow_ema = data['Close'].ewm(span=slow_period, min_periods=slow_period).mean()
    data['MACD'] = fast_ema - slow_ema
    data['MACD_Signal'] = data['MACD'].ewm(span=signal_period, min_periods=signal_period).mean()
    data['MACD_Histogram'] = data['MACD'] - data['MACD_Signal']
    return data

def identify_macd_peaks_and_troughs_using_derivative(data):
    # Calculate the first derivative (rate of change) of the MACD Histogram
    data['MACD_Histogram_Delta'] = data['MACD_Histogram'].diff()

    # Initialize columns for peaks and troughs
    data['Green_Peak'] = False
    data['Red_Peak'] = False

    # Iterate over the data
    for i in range(1, len(data)):
        # Check for Green Peak (MACD Histogram peak)
        if data['MACD_Histogram_Delta'].iloc[i - 1] > 0 and data['MACD_Histogram_Delta'].iloc[i] <= 0:
            data['Green_Peak'].iloc[i] = True

        # Check for Red Trough (MACD Histogram trough)
        if data['MACD_Histogram_Delta'].iloc[i - 1] < 0 and data['MACD_Histogram_Delta'].iloc[i] >= 0:
            data['Red_Peak'].iloc[i] = True

    return data

# Backtesting function

# Backtesting function
def backtest_strategy(data, initial_capital=10000):
    capital = initial_capital
    position = 0
    trade_log = []

    for index, row in data.iterrows():
        # Buy logic at Red Trough (potential uptrend reversal)
        if row['Red_Peak'] and capital > 0:
            position = capital / row['Close']
            capital = 0
            trade_log.append((index, 'BUY', row['Close'], position, capital))

        # Sell logic at Green Peak (potential downtrend reversal)
        elif row['Green_Peak'] and position > 0:
            capital = position * row['Close']
            position = 0
            trade_log.append((index, 'SELL', row['Close'], position, capital))

    final_valuation = capital + position * data.iloc[-1]['Close']
    print(f"Initial capital: {initial_capital}")
    print(f"Final valuation: {final_valuation}")
    return final_valuation, trade_log

# Fetch historical data
historical_data = fetch_historical_data(symbol, interval, lookback)

# Compute indicators
historical_data = compute_rsi(historical_data)
historical_data = calculate_macd(historical_data)
historical_data = identify_macd_peaks_and_troughs_using_derivative(historical_data)

# Backtest the strategy
final_valuation, trade_log = backtest_strategy(historical_data)

# Print trade log
for trade in trade_log:
    print(f"Timestamp: {trade[0]}, Action: {trade[1]}, Price: {trade[2]}, Position: {trade[3]}, Capital: {trade[4]}")