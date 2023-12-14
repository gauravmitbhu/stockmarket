import requests
import json
import datetime
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
import os
import numpy as np
from pandas.errors import SettingWithCopyWarning

# Use your own API key and secret
api_key = os.getenv('BINANCE_API_KEY')
api_secret = os.getenv('BINANCE_API_SECRET')

# Define the Binance API endpoint for K-line data
endpoint = 'https://api.binance.com/api/v3/klines'

# Define the parameters for the API request
symbol = 'BTCUSDT'
#interval = '15m'
interval = '1h'
limit = 1000
days_to_fetch=300

#Technical parameters
rsi_window = 14
buy_rsi_upper_limit70 = 70
sell_rsi_upper_limit30 = 30

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

def compute_rsi(data, window=rsi_window): #using window=14 gives poor results, 7 is good for 15m data
    delta = data.diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def identify_macd_peaks_and_troughs_using_derivative(data): #Using normal macd crossover gives poor results
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

# Function to fetch data from Binance
def fetch_data(symbol, interval, limit, days_to_fetch):
    """
    Fetches data from Binance and saves it to an Excel file.
    Checks if the last 15-minute slot file already exists to avoid unnecessary downloads.
    """
    # Round down the current time to the nearest 15-minute slot
    current_time = datetime.datetime.now()
    rounded_time = current_time - datetime.timedelta(minutes=current_time.minute % 15,
                                                     seconds=current_time.second,
                                                     microseconds=current_time.microsecond)
    filename = f"{symbol}_{interval}_{days_to_fetch}d_{rounded_time.strftime('%Y-%m-%d_%H-%M')}.xlsx"

    # Check if file already exists
    if os.path.exists(filename):
        print(f"Data file {filename} already exists. Skipping download.")
        return pd.read_excel(filename, index_col=0)

    # Fetch data from Binance
    start_time = int((rounded_time - datetime.timedelta(days=days_to_fetch)).timestamp() * 1000)
    params = {'symbol': symbol, 'interval': interval, 'startTime': start_time, 'limit': limit}
    response = requests.get(endpoint, params=params)
    klines = json.loads(response.text)

    # Process and save data to Excel
    ohlc_data = [[float(k[1]), float(k[2]), float(k[3]), float(k[4])] for k in klines]
    df = pd.DataFrame(ohlc_data, columns=['Open', 'High', 'Low', 'Close'])
    df['Timestamp'] = [datetime.datetime.fromtimestamp(int(k[0]) / 1000) for k in klines]
    df.set_index('Timestamp', inplace=True)
    df.to_excel(filename)
    print(f"Data saved to {filename}")
    return df

# Function to read data from Excel
def read_data_from_excel():
    excel_file_path = 'BTC-USD_data_60d_15m_endtime-10-12-2023.xlsx'
    return pd.read_excel(excel_file_path, index_col='Datetime')
    #excel_file_path = 'btc_data_binance_15m_60d.xlsx'
    #return pd.read_excel(excel_file_path, index_col='Timestamp')

def calculate_macd_and_rsi(df):
    calculate_macd(df)
    df['RSI'] = compute_rsi(df['Close'])  # Make sure to assign the Series returned by compute_rsi
    df['ATR'] = calculate_atr(df)
    identify_macd_peaks_and_troughs_using_derivative(df)

# Plotting function
def plot_data(df):
    # Customize market colors and style
    mc = mpf.make_marketcolors(up='green', down='red', inherit=True)
    s = mpf.make_mpf_style(base_mpf_style='charles', marketcolors=mc)

    # Define additional plots for MACD and RSI
    apds = [mpf.make_addplot(df['MACD'], panel=1, color='fuchsia', ylabel='MACD'),
            mpf.make_addplot(df['Signal'], panel=1, color='b'),
            mpf.make_addplot(df['MACD_Histogram'], panel=1, type='bar', color='dimgray', ylabel='Histogram'),
            mpf.make_addplot(df['RSI'], panel=2, color='purple', ylabel='RSI')]

    # Plot using mplfinance with panel ratios
    mpf.plot(df, type='candle', style=s, addplot=apds, title='BTC/USDT OHLC', panel_ratios=(6,3,2))

def trading_strategy(data, initial_capital):
    maker_taker_fee = 0.00075

    # Calculate MACD and Signal Line
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()
    data['MACD_Histogram'] = data['MACD'] - data['Signal_Line']

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

        if buy_signal[i] and not position_held  and portfolio['cash'][i - 1] > 0 and data['RSI'][i] < buy_rsi_upper_limit70 and data['ATR'][i] < 1000:
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

        elif sell_signal[i] and position_held and portfolio['holdings'][i - 1] > 0 and data['RSI'][i] > sell_rsi_upper_limit30 and data['ATR'][i] < 1000:
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

# Suppress FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)

# Initial setup for the plot
#plt.ion()
#fig, axes = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})

# Main loop
while True:
    btc_data = fetch_data(symbol, interval, limit, days_to_fetch)
    #btc_data = read_data_from_excel()  # Read data from Excel
    calculate_macd_and_rsi(btc_data)
    # Run the trading strategy
    initial_capital = 100
    portfolio, trade_log, value_if_held = trading_strategy(btc_data, initial_capital)
    for i in range(len(trade_log)):
        print(trade_log[i])

    final_portfolio_value = portfolio['total'].iloc[-1]
    print(f"Final Portfolio Value: {final_portfolio_value}")

    # Print value if held
    print(f"\nValue if held from start to end: {value_if_held}")
    #plot_data(btc_data)
    plt.pause(60*15)  # pause for 15 minutes