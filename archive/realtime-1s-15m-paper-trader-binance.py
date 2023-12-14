import requests
import pandas as pd
import datetime
import os
import time
import numpy as np
from binance import Client
from pandas.errors import SettingWithCopyWarning

# Initialize Binance client
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
client = Client(api_key, api_secret)

symbol = 'BTCUSDT'
csv_filename = 'BTCUSDT-1s-data.csv'

# Technical analysis functions
def calculate_atr(data, window=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window).mean()
    return atr

# Function to calculate MACD and signal line
def calculate_macd(df):
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=9, adjust=False).mean()
    df['MACD'] = macd
    df['Signal'] = signal
    df['MACD_Histogram'] = macd - signal

def compute_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, np.nan)
    loss = -delta.where(delta < 0, np.nan)

    avg_gain = gain.rolling(window=window, min_periods=1).mean().fillna(0)
    avg_loss = loss.rolling(window=window, min_periods=1).mean().fillna(0)

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    data['RSI'] = rsi
    return data

def compute_rsi2(data, window=7):
    delta = data['Close'].diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    data['RSI'] = rsi
    return rsi

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

# Function to get current ticker price
def get_current_price():
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

# Function to update CSV with the latest price
# Function to update CSV with the latest price and indicators
# Function to update CSV with the latest price and indicators
def update_csv(filename, price):
    timestamp = datetime.datetime.now()
    new_data = pd.DataFrame({'Timestamp': [timestamp], 'Close': [price]})
    new_data.set_index('Timestamp', inplace=True)

    if os.path.exists(filename):
        # Read existing data
        existing_data = pd.read_csv(filename, index_col='Timestamp', parse_dates=True)
        # Append new data
        combined_data = pd.concat([existing_data, new_data])
        # Update indicators
        calculate_macd(combined_data)
        #compute_rsi(combined_data)
        compute_rsi2(combined_data)
        identify_macd_peaks_and_troughs_using_derivative(combined_data)
        # Save updated data
        combined_data.to_csv(filename)
    else:
        # Initialize indicators for new data
        new_data['MACD'] = np.nan
        new_data['Signal'] = np.nan
        new_data['MACD_Histogram'] = np.nan
        new_data['RSI'] = np.nan
        new_data['Green_Peak'] = False
        new_data['Red_Peak'] = False
        new_data.to_csv(filename)

def make_trading_decision(df):
    global portfolio  # Declare portfolio as a global variable
    global last_buy_price
    global last_sell_price

    # Process only the latest data
    i = len(df) - 1
    current_price, price_time = df['Close'].iloc[-1], df.index[-1]

    # Print the latest price and indicators
    print("Current Price,Buy=Red Peak, Sell=Green Peak, RSI(buy<30,sell>70))")
    print(current_price, df['Red_Peak'].iloc[-1],df['Green_Peak'].iloc[-1], df['RSI'].iloc[-1])

    # Check for green peak and RSI < 30
    if df['Red_Peak'].iloc[-1] and df['RSI'].iloc[-1] < 30 and portfolio['cash'].iloc[-1] > 0:
        #Buy Logic
        print("price good enouhg")
        transaction_cost = portfolio['cash'].iloc[-1] * maker_taker_fee
        invest_amount = portfolio['cash'].iloc[-1] - transaction_cost
        new_holdings = invest_amount / current_price
        new_cash = 0
        new_total = new_cash + new_holdings * current_price
        last_buy_price = current_price

        # Create a new DataFrame for the updated portfolio row
        new_row = pd.DataFrame({'holdings': [new_holdings], 'cash': [new_cash], 'total': [new_total]}, index=[price_time])

        # Concatenate the new row with the portfolio DataFrame
        portfolio = pd.concat([portfolio, new_row])

        position_held = True

        print(f'Position Held: {position_held}, Portfolio Holdings: {new_holdings}, Portfolio Cash: {new_cash}, Portfolio Total: {new_total}, Current Price: {current_price}, Current Time: {price_time}, Buy Signal: {df["Green_Peak"].iloc[-1]}, Sell Signal: {df["Red_Peak"].iloc[-1]}, RSI: {df["RSI"].iloc[-1]}')

        return "Buy"

    # Check for red peak and RSI > 70
    if df['Green_Peak'].iloc[-1] and df['RSI'].iloc[-1] > 70 and portfolio['holdings'].iloc[-1] > 0:
        # Sell Logic
        if(current_price-last_buy_price)/last_buy_price > maker_taker_fee:
            sell_value = portfolio['holdings'].iloc[-1] * current_price
            transaction_cost = sell_value * maker_taker_fee
            new_cash = sell_value - transaction_cost
            new_holdings = 0
            new_total = new_cash + new_holdings * current_price
            last_sell_price = current_price

            # Create a new DataFrame for the updated portfolio row
            new_row = pd.DataFrame({'holdings': [new_holdings], 'cash': [new_cash], 'total': [new_total]}, index=[price_time])

            # Concatenate the new row with the portfolio DataFrame
            portfolio = pd.concat([portfolio, new_row])

            position_held = False

            print(f'Position Held: {position_held}, Portfolio Holdings: {new_holdings}, Portfolio Cash: {new_cash}, Portfolio Total: {new_total}, Current Price: {current_price}, Current Time: {price_time}, Buy Signal: {df["Green_Peak"].iloc[-1]}, Sell Signal: {df["Red_Peak"].iloc[-1]}, RSI: {df["RSI"].iloc[-1]}')

            return "Sell"
        else:
            print("sell signal but price not good enough")
            return "Hold"
    return "Hold"

# Suppress FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)

# Initialize initial capital
initial_capital = 5000

# Initialize portfolio as a list of dictionaries
portfolio = [{'holdings': 0, 'cash': initial_capital, 'total': initial_capital}]

# Create a DataFrame from the list of dictionaries
portfolio = pd.DataFrame(portfolio)

trade_log = []
# New variable to track if a position is held
position_held = False
maker_taker_fee = 0.00075
last_buy_price = 999999
last_sell_price = -999999

while True:
    current_price = get_current_price()
    update_csv(csv_filename, current_price)
    df = pd.read_csv(csv_filename, index_col='Timestamp', parse_dates=True)
    decision = make_trading_decision(df)
    # Calculate the latest total value based on the latest holdings and current price
    latest_holdings = portfolio['holdings'].iloc[-1]
    current_price = get_current_price()
    latest_total = latest_holdings * current_price

    # Print the trading decision, latest cash, and latest total holdings value
    print(
        f"Trading Decision at {datetime.datetime.now()}: {decision}, Cash: {portfolio['cash'].iloc[-1]}, Holdings: {latest_holdings * current_price}")

    # Wait for 15 minutes
    print("Next update in 15 minutes at", datetime.datetime.now() + datetime.timedelta(minutes=15))
    time.sleep(1)  # Check the price every second

