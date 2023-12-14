import os
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pandas.errors import SettingWithCopyWarning

# Define the cryptocurrency symbol
crypto_symbol = "BTC-USD"

# Load data
#excel_file_path = 'BTC-USD_data_60d_1h.xlsx'
#excel_file_path = 'bitcoin_data_5yr.xlsx'
#excel_file_path = 'BTC-USD_data_60d_1h_bear_2022-03-28.xlsx'
#excel_file_path = 'BTC-USD_data_60d_15m_endtime-10-12-2023.xlsx'
#excel_file_path = 'btc_data_binance_15m_60d.xlsx'
excel_file_path = 'BTCUSDT_5_years_data.xlsx'
btc_data = pd.read_excel(excel_file_path, index_col=0, parse_dates=True)

def calculate_atr(data, window=7):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window).mean()
    return atr

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

def trading_strategy(data, initial_capital):
    maker_taker_fee = 0.00075

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

        if buy_signal[i] and not position_held  and portfolio['cash'][i - 1] > 0 and data['RSI'][i] < 50 and data['ATR'][i] < 1000:
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
            # print({
            #     'Date': date,
            #     'Action': 'Buy',
            #     'Price': data['Close'][i],
            #     'BTC_Amount': invest_amount / data['Close'][i],
            #     'Cash_Used': invest_amount,
            #     'RSI': data['RSI'][i],
            #     'ATR': data['ATR'][i]
            # })
            position_held = True

        elif sell_signal[i] and position_held and portfolio['holdings'][i - 1] > 0 and data['RSI'][i] > 50 and data['ATR'][i] < 1000:
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
            # print({
            #     'Date': date,
            #     'Action': 'Sell',
            #     'Price': data['Close'][i],
            #     'BTC_Amount': portfolio['holdings'][i - 1],
            #     'Cash_Gained': sell_value,
            #     'RSI': data['RSI'][i],
            #     'ATR': data['ATR'][i]
            # })
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

# Define the trading period and step back
days_in_period = 300
step_back_days = 30
initial_capital = 5000

# Initialize a list to store results
results = []

# Iterate over the data in chunks, starting from the latest date
for start_date in pd.date_range(start=btc_data.index.max() - pd.DateOffset(days=days_in_period), end=btc_data.index.min(), freq=f'-{step_back_days}D'):
    end_date = start_date + pd.DateOffset(days=days_in_period)
    data_chunk = btc_data[(btc_data.index >= start_date) & (btc_data.index <= end_date)]

    # Apply trading strategy to this chunk
    portfolio, trade_log, value_if_held = trading_strategy(data_chunk, initial_capital)

    # Store or display the results
    final_portfolio_value = portfolio['total'].iloc[-1]
    results.append({
        'Start Date': start_date,
        'End Date': end_date,
        'Final Portfolio Value': final_portfolio_value,
        'Value if Held': value_if_held
    })
    print({
        'Start Date': start_date,
        'End Date': end_date,
        'Final Portfolio Value': final_portfolio_value,
        'Value if Held': value_if_held
    })

# Convert results to DataFrame
results_df = pd.DataFrame(results)

# Display the results
print(results_df)

# Optional: Plot the results
plt.figure(figsize=(10, 5))
plt.plot(results_df['End Date'], results_df['Final Portfolio Value'], label='Final Portfolio Value')
plt.plot(results_df['End Date'], results_df['Value if Held'], label='Value if Held')
plt.xlabel('End Date of Each Period')
plt.ylabel('Value')
plt.title('Backtesting Results Over Time')
plt.legend()
plt.show()