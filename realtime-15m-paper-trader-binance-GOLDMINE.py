import requests
import pandas as pd
import datetime
import os
import time
import numpy as np
from binance import Client
from pandas.errors import SettingWithCopyWarning
import json
from pytz import timezone


# Initialize Binance client
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')
client = Client(api_key, api_secret)

symbol = 'BTCUSDT'
csv_filename = 'BTCUSDT-1s-data.csv'

# Technical analysis functions
def calculate_atr(data, window=7):
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

def compute_rsi(data, window=7):
    delta = data.diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    return rsi


def identify_macd_peaks_and_troughs_using_derivative(data):
    # Calculate the first derivative (rate of change) of the MACD Histogram
    data['MACD_Histogram_Delta'] = data['MACD_Histogram'].diff()

    # Initialize columns for peaks and troughs
    data['Green_Peak'] = False
    data['Red_Peak'] = False

    # Iterate over the data
    for i in range(2, len(data)):
        # Check for Green Peak (MACD Histogram peak)
        if data['MACD_Histogram_Delta'].iloc[i - 1] > 0 and data['MACD_Histogram_Delta'].iloc[i] <= 0:
            data['Green_Peak'].iloc[i - 1] = True

        # Check for Red Trough (MACD Histogram trough)
        if data['MACD_Histogram_Delta'].iloc[i - 1] < 0 and data['MACD_Histogram_Delta'].iloc[i] >= 0:
            data['Red_Peak'].iloc[i - 1] = True

    return data

def buy_signal_macd_peaks(data):
    identify_macd_peaks_and_troughs_using_derivative(data)
    return data['Red_Peak']

def sell_signal_macd_peaks(data):
    identify_macd_peaks_and_troughs_using_derivative(data)
    return data['Green_Peak']

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
        compute_rsi(combined_data)
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

def trading_strategy_retrospective(data, initial_capital):
    # Calculate MACD and Signal Line
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    data['MACD_Histogram'] = data['MACD'] - data['Signal_Line']

    # RSI and ATR
    data['RSI'] = compute_rsi(data['Close'])
    data['ATR'] = calculate_atr(data)

    # Initialize portfolio and trade log
    portfolio = pd.DataFrame(index=data.index)
    portfolio['holdings'] = np.zeros(len(data))
    portfolio['cash'] = np.zeros(len(data))
    portfolio['cash'][0] = initial_capital
    portfolio['total'] = portfolio['cash']
    trade_log = []
    # Generate signals based on MACD peaks
    buy_signal = buy_signal_macd_peaks(data)
    sell_signal = sell_signal_macd_peaks(data)

    # New variable to track if a position is held
    position_held = False

    for i in range(1, len(data)):

        portfolio['holdings'][i] = portfolio['holdings'][i - 1]
        portfolio['cash'][i] = portfolio['cash'][i - 1]

        date = data.index[i]

        if buy_signal[i] and not position_held  and portfolio['cash'][i - 1] > 0 and data['RSI'][i] < rsi_lower_limit and data['ATR'][i] < 1000:
            # Calculate transaction cost
            transaction_cost = portfolio['cash'][i - 1] * maker_taker_fee
            invest_amount = portfolio['cash'][i - 1] - transaction_cost
            portfolio['holdings'][i] = invest_amount / data['Close'][i]
            portfolio['cash'][i] = 0
            #print(f"{date} - Buy: Price = {data['Close'][i]}, Amount = {invest_amount}")
            trade_log.append({
                'Date': date,
                'Action': 'Buy',
                'Price': data['Close'][i],
                'BTC_Amount': invest_amount / data['Close'][i],
                'Cash_Used': invest_amount,
                'RSI': data['RSI'][i],
                'ATR': data['ATR'][i]
            })
            print({
                'Date': date,
                'Action': 'Buy',
                'Price': data['Close'][i],
                'BTC_Amount': invest_amount / data['Close'][i],
                'Cash_Used': invest_amount,
                'RSI': data['RSI'][i],
                'ATR': data['ATR'][i]
            })
            position_held = True

        elif sell_signal[i] and position_held and portfolio['holdings'][i - 1] > 0 and data['RSI'][i] > rsi_upper_limit and data['ATR'][i] < 1000:
            # Calculate transaction cost
            sell_value = portfolio['holdings'][i - 1] * data['Close'][i]
            transaction_cost = sell_value * maker_taker_fee
            portfolio['cash'][i] = sell_value - transaction_cost
            #print(f"{date} - Sell: Price = {data['Close'][i]}, Amount = {sell_value}")
            portfolio['holdings'][i] = 0
            trade_log.append({
                'Date': date,
                'Action': 'Sell',
                'Price': data['Close'][i],
                'BTC_Amount': portfolio['holdings'][i - 1],
                'Cash_Gained': sell_value,
                'RSI': data['RSI'][i],
                'ATR': data['ATR'][i]
            })
            print({
                'Date': date,
                'Action': 'Sell',
                'Price': data['Close'][i],
                'BTC_Amount': portfolio['holdings'][i - 1],
                'Cash_Gained': sell_value,
                'RSI': data['RSI'][i],
                'ATR': data['ATR'][i]
            })
            position_held = False

        # Update total portfolio value
        portfolio['total'][i] = portfolio['cash'][i] + portfolio['holdings'][i] * data['Close'][i]

    # Calculate holding value
    start_price = data.iloc[0]['Close']
    end_price = data.iloc[-1]['Close']
    value_if_held = initial_capital * (end_price / start_price)

    return portfolio, trade_log, value_if_held

def trading_strategy_single_realtime(data):
    global portfolio
    # Calculate MACD and Signal Line
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    data['MACD_Histogram'] = data['MACD'] - data['Signal_Line']

    # RSI and ATR
    data['RSI'] = compute_rsi(data['Close'])
    data['ATR'] = calculate_atr(data)

    latest_timestamp = data.index[-1]

    # Initialize portfolio and trade log
    if latest_timestamp not in portfolio.index:
        new_row_values = portfolio.iloc[-1].copy()
        portfolio.loc[latest_timestamp] = new_row_values

    # Generate signals based on MACD peaks
    buy_signal = buy_signal_macd_peaks(data)
    sell_signal = sell_signal_macd_peaks(data)

    # New variable to track if a position is held
    i = len(data) -1

    portfolio['holdings'][i] = portfolio['holdings'][i - 1]
    portfolio['cash'][i] = portfolio['cash'][i - 1]

    date = data.index[i]
    latest_price=get_current_price()

    print(f"Buy signal:{buy_signal[i]}, Sell signal:{sell_signal[i]}, RSI:{data['RSI'][i]}",)
    print("Portfolio holdings:", portfolio['holdings'][i])
    print("Portfolio cash:", portfolio['cash'][i])

    if buy_signal[i] and portfolio['cash'][i - 1] > 0 and data['RSI'][i] < rsi_lower_limit and data['ATR'][i] < 1000:
        # Calculate transaction cost
        transaction_cost = portfolio['cash'][i - 1] * maker_taker_fee
        invest_amount = portfolio['cash'][i - 1] - transaction_cost
        #portfolio['holdings'][i] = invest_amount / data['Close'][i]
        portfolio['holdings'][i] = invest_amount / latest_price

        portfolio['cash'][i] = 0
        # print(f"{date} - Buy: Price = {data['Close'][i]}, Amount = {invest_amount}")
        trade_log.append({
            'Date': date,
            'Action': 'Buy',
            #'Price': data['Close'][i],
            #'BTC_Amount': invest_amount / data['Close'][i],
            'Price': latest_price,
            'BTC_Amount': invest_amount / latest_price,
            'Cash_Used': invest_amount,
            'RSI': data['RSI'][i],
            'ATR': data['ATR'][i]
        })
        print({
            'Date': date,
            'Action': 'Buy',
            # 'Price': data['Close'][i],
            # 'BTC_Amount': invest_amount / data['Close'][i],
            'Price': latest_price,
            'BTC_Amount': invest_amount / latest_price,
            'Cash_Used': invest_amount,
            'RSI': data['RSI'][i],
            'ATR': data['ATR'][i]
        })
        position_held = True
    elif sell_signal[i] and portfolio['holdings'][i - 1] > 0 and data['RSI'][i] > rsi_upper_limit and data['ATR'][i] < 1000:
        # Calculate transaction cost
        # sell_value = portfolio['holdings'][i - 1] * data['Close'][i]
        sell_value = portfolio['holdings'][i - 1] * latest_price
        transaction_cost = sell_value * maker_taker_fee
        portfolio['cash'][i] = sell_value - transaction_cost
        # print(f"{date} - Sell: Price = {data['Close'][i]}, Amount = {sell_value}")
        portfolio['holdings'][i] = 0
        trade_log.append({
            'Date': date,
            'Action': 'Sell',
            #'Price': data['Close'][i],
            'Price': latest_price,
            'BTC_Amount': portfolio['holdings'][i - 1],
            'Cash_Gained': sell_value,
            'RSI': data['RSI'][i],
            'ATR': data['ATR'][i]
        })
        print({
            'Date': date,
            'Action': 'Sell',
            #'Price': data['Close'][i],
            'Price': latest_price,
            'BTC_Amount': portfolio['holdings'][i - 1],
            'Cash_Gained': sell_value,
            'RSI': data['RSI'][i],
            'ATR': data['ATR'][i]
        })

    # Update total portfolio value
    #portfolio['total'][i] = portfolio['cash'][i] + portfolio['holdings'][i] * data['Close'][i]
    portfolio['total'][i] = portfolio['cash'][i] + portfolio['holdings'][i] * latest_price

    # Calculate holding value
    start_price = data.iloc[0]['Close']
    #end_price = data.iloc[-1]['Close']
    end_price = latest_price
    value_if_held = initial_capital * (end_price / start_price)

    return portfolio, trade_log, value_if_held

# Function to fetch data from Binance API
def fetch_data(filename, start_timestamp, end_timestamp=None):
    interval_seconds = interval_to_seconds(interval)

    # Set default end_timestamp if not provided
    end_timestamp = end_timestamp or int(datetime.datetime.now().timestamp() * 1000)

    # Check if the file exists and read existing data
    if os.path.exists(filename):
        existing_data = pd.read_excel(filename, index_col='Timestamp', parse_dates=True)
        updated = False
        if not existing_data.empty:
            first_timestamp = int(existing_data.index[0].timestamp() * 1000)
            last_timestamp = int(existing_data.index[-1].timestamp() * 1000)
            if start_timestamp + interval_seconds * 1000 < first_timestamp:
                first_data = request_and_process_data(start_timestamp, first_timestamp)
                existing_data = pd.concat([first_data, existing_data]).drop_duplicates(keep='first')
                updated = True
            if end_timestamp > last_timestamp  + interval_seconds * 1000:
                last_data = request_and_process_data(last_timestamp+1, end_timestamp)
                existing_data = pd.concat([existing_data, last_data]).drop_duplicates(keep='first')
                updated = True
            if updated:
                existing_data.reset_index().drop_duplicates(subset='Timestamp', keep='first').set_index('Timestamp')
                existing_data.to_excel(filename)
    else:
        # If file doesn't exist, fetch and save new data
        new_data = request_and_process_data(start_timestamp, end_timestamp)

        new_data = new_data.reset_index().drop_duplicates(subset='Timestamp', keep='first').set_index('Timestamp')

        new_data.to_excel(filename)
        return new_data

    return existing_data if updated else None

def interval_to_seconds(interval):
    if interval.endswith('m'):
        return int(interval[:-1]) * 60
    elif interval.endswith('h'):
        return int(interval[:-1]) * 3600
    elif interval.endswith('d'):
        return int(interval[:-1]) * 86400
    else:
        raise ValueError("Unsupported interval format")

# Function to request and process data from Binance API
def request_and_process_data(start_timestamp, end_timestamp, df_old=None):
    interval_seconds = interval_to_seconds(interval)
    df = df_old if df_old is not None else pd.DataFrame()
    while True:
        params = {'symbol': symbol, 'interval': interval, 'startTime': start_timestamp, 'endTime': end_timestamp, 'limit': limit}
        response = requests.get(endpoint, params=params)
        klines = json.loads(response.text)

        # Process the new data
        processed_data = [[float(kline[1]), float(kline[2]), float(kline[3]), float(kline[4])] for kline in klines]
        df_new = pd.DataFrame(processed_data, columns=['Open', 'High', 'Low', 'Close'])
        timestamps = [datetime.datetime.fromtimestamp(int(kline[0]) / 1000) for kline in klines]
        df_new['Timestamp'] = timestamps
        df_new.set_index('Timestamp', inplace=True)

        df = pd.concat([df, df_new]).drop_duplicates(keep='first')

        # Check if the last timestamp in the dataframe is beyond the end_timestamp
        if df.index[-1].timestamp() * 1000 + interval_seconds * 1000 >= end_timestamp:
            break

        # Update start_timestamp for the next iteration to continue from the last fetched timestamp
        start_timestamp = int(df.index[-1].timestamp() * 1000) + 1

    return df


# Function to calculate the next target time
def next_target_time(interval):
    now = datetime.datetime.now()

    if interval.endswith('m'):
        minutes = int(interval[:-1])
        next_time = now.replace(second=0, microsecond=0) + datetime.timedelta(minutes=minutes - now.minute % minutes)
    elif interval.endswith('h'):
        hours = int(interval[:-1])
        next_time = now.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=hours - now.hour % hours)
    else:
        raise ValueError("Unsupported interval format")

    return next_time
def get_current_price():
    ticker = client.get_symbol_ticker(symbol=symbol)
    return float(ticker['price'])

def calculate_next_timestamp(current_time, interval):
    if interval.endswith('m'):
        minutes = int(interval[:-1])
        next_time = current_time.replace(second=0, microsecond=0) + datetime.timedelta(minutes=minutes - current_time.minute % minutes)
    elif interval.endswith('h'):
        hours = int(interval[:-1])
        next_time = current_time.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=hours - current_time.hour % hours)
    else:
        raise ValueError("Unsupported interval format")
    return next_time


def get_btc_data_for_dates(start_timestamp, end_timestamp):
    full_btc_data = pd.read_excel(filename, index_col='Timestamp', parse_dates=True)

    # Convert timestamps to datetime objects
    start_datetime = pd.to_datetime(start_timestamp, unit='ms')
    end_datetime = pd.to_datetime(end_timestamp, unit='ms')

    # Slice using datetime objects
    trim_btc_data = full_btc_data.loc[start_datetime:end_datetime]
    return trim_btc_data

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

symbol = 'BTCUSDT'
#interval = '1m'
interval = '15m'
#interval = '1h'
limit = 1000
days_to_fetch=1
# Define the Binance API endpoint for K-line data
endpoint = 'https://api.binance.com/api/v3/klines'
filename = 'btc_data_binance_'+interval+'-GOLDMINE.xlsx'
rsi_upper_limit=10
rsi_lower_limit=90

start_timestamp = int((datetime.datetime.now() - datetime.timedelta(days=days_to_fetch)).timestamp() * 1000)
end_timestamp = int(datetime.datetime.now().timestamp() * 1000)
fetch_data(filename, start_timestamp=start_timestamp)
btc_data = get_btc_data_for_dates(start_timestamp, end_timestamp)

portfolio, trade_log, value_if_held = trading_strategy_retrospective(btc_data, initial_capital)

#Value if held and profit
print("Total value:", portfolio['total'].iloc[-1])
print("Profit in trading:", (portfolio['total'].iloc[-1] - initial_capital)/initial_capital*100, "%")
print("Value if held:" , value_if_held)
print("Profit in holding:", (value_if_held - initial_capital)/initial_capital*100, "%")
print("Total number of trades:", len(trade_log))
print("Total days traded:", days_to_fetch)

print("Now trading in real time..............")

while True:
    # Calculate next target time
    target_time = next_target_time(interval)
    current_time = datetime.datetime.now()

    # Wait until the target time
    while current_time < target_time:
        print(f"Waiting until {target_time}...+5 seconds")
        time.sleep((target_time - current_time).total_seconds()+5)
        current_time = datetime.datetime.now()

    # Fetch data and check if the next timestamp exists in the dataframe
    while target_time not in btc_data.index:
        fetch_data(filename, start_timestamp)
        #btc_data = pd.read_excel(filename, index_col='Timestamp', parse_dates=True)
        btc_data = get_btc_data_for_dates(start_timestamp, target_time.timestamp() * 1000)
        if target_time in btc_data.index:
            break
        time.sleep(1)  # Adjust sleep time as needed

    old_length_trade_log = len(trade_log)
    portfolio, trade_log, value_if_held = trading_strategy_single_realtime(btc_data)

    # Check if a new trade was executed
    if len(trade_log) > old_length_trade_log:
        last_trade = trade_log[-1]
        print("TRADE EXECUTED!")
        #print(last_trade)

    # Value if held and profit
    print("Current time:", datetime.datetime.now())
    print("Total value:", portfolio['total'].iloc[-1])
    print("Profit in trading:", (portfolio['total'].iloc[-1] - initial_capital) / initial_capital * 100, "%")
    print("Value if held:", value_if_held)
    print("Profit in holding:", (value_if_held - initial_capital) / initial_capital * 100, "%")
    print("Total number of trades:", len(trade_log))
    print("Total days traded:", days_to_fetch)

