import os
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Define the cryptocurrency symbol
crypto_symbol = "BTC-USD"

# Fetch data for the last 2 years and save to a CSV file
# btc_data = yf.download(crypto_symbol, period="2y")
# btc_data.to_csv('./bitcoin_data_2y.csv')  # Save to CSV

#csv_file_path = 'bitcoin_data_jan-022-dec-2023.csv'
#btc_data = pd.read_csv(csv_file_path, index_col=0, parse_dates=True)

excel_file_path = 'bitcoin_data_5yr.xlsx'
btc_data = pd.read_excel(excel_file_path, index_col=0, parse_dates=True)

def calculate_support_resistance(data, end_date, lookback_period=20):
    relevant_data = data[:end_date].tail(lookback_period)
    support = relevant_data['Low'].min()
    resistance = relevant_data['High'].max()
    return support, resistance


def compute_rsi(data, window=14):
    delta = data.diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def simple_sell_signal(data):
    #simple sell signal based on MACD and RSI
    sell_signal = (data['MACD'] < data['Signal_Line']) & (data['RSI'] > 65)
    return sell_signal

def simple_buy_signal(data):
    #simple buy signal based on MACD and RSI
    buy_signal = (data['MACD'] > data['Signal_Line']) & (data['RSI'] < 35)
    return buy_signal

def identify_macd_peaks_and_troughs(data):
    """
    Identify MACD histogram peaks and troughs.
    Green peaks: Points where the histogram is higher than both the previous and next bars.
    Red troughs: Points where the histogram is lower than both the previous and next bars.
    """
    data['Green_Peak'] = False
    data['Red_Peak'] = False

    for i in range(1, len(data) - 1):
        if data['MACD_Histogram'].iloc[i] > data['MACD_Histogram'].iloc[i-1] and data['MACD_Histogram'].iloc[i] > data['MACD_Histogram'].iloc[i+1]:
            data['Green_Peak'].iloc[i] = True
        elif data['MACD_Histogram'].iloc[i] < data['MACD_Histogram'].iloc[i-1] and data['MACD_Histogram'].iloc[i] < data['MACD_Histogram'].iloc[i+1]:
            data['Red_Peak'].iloc[i] = True

    return data


def buy_signal_macd_peaks(data):
    """
    Generate buy signals based on MACD peaks.
    """
    identify_macd_peaks_and_troughs(data)
    return data['Red_Peak']

def sell_signal_macd_peaks(data):
    """
    Generate sell signals based on MACD peaks.
    """
    identify_macd_peaks_and_troughs(data)
    return data['Green_Peak']

def trading_strategy(data, initial_capital):
    # Calculate MACD and Signal Line indicators
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # Calculate RSI
    data['RSI'] = compute_rsi(data['Close'])

    # Generate MACD histogram
    data['MACD_Histogram'] = data['MACD'] - data['Signal_Line']

    # Generate signals based on MACD and RSI
    # buy_signal = simple_buy_signal(data)
    # sell_signal = simple_sell_signal(data)

    # Generate signals based on MACD peaks
    buy_signal = buy_signal_macd_peaks(data)
    sell_signal = sell_signal_macd_peaks(data)

    # Initialize portfolio
    portfolio = pd.DataFrame(index=data.index)
    portfolio['holdings'] = np.zeros(len(data))
    portfolio['cash'] = np.zeros(len(data))
    portfolio['cash'][0] = initial_capital
    portfolio['trades'] = 0  # Counter for trades

    # Initialize the DataFrame to store trade details
    trade_log = []

    trade_dates = []  # To store the dates of trades for plotting

    last_trade_price = 999999  # To store the price of the last trade

    for i in range(1, len(data)):
        # Calculate support and resistance up to the current date
        support, resistance = calculate_support_resistance(data, data.index[i])

        # Limit to two trades per week
        if portfolio['trades'][i-1] < 2:
            if buy_signal[i] and portfolio['cash'][i-1] > 0 and data['RSI'][i] < 30:
            #if buy_signal[i] and portfolio['cash'][i - 1] > 0 and last_trade_price > data['Close'][i] and data['RSI'][i] < 50:
                portfolio['holdings'][i] = portfolio['cash'][i-1] / data['Close'][i]
                portfolio['cash'][i] = 0
                portfolio['trades'][i] = portfolio['trades'][i-1] + 1
                btc_amount = portfolio['cash'][i - 1] / data['Close'][i]
                trade_log.append({
                    'Date': data.index[i],
                    'Action': 'Buy',
                    'Price': data['Close'][i],
                    'BTC_Amount': btc_amount,
                    'Cash_Used': portfolio['cash'][i - 1],
                    'RSI': data['RSI'][i],  # Record RSI value at the time of trade.
                    'Support': support,
                    'Resistance': resistance
                })
                last_trade_price = data['Close'][i]
                trade_dates.append(data.index[i])  # Record trade date
            #elif sell_signal[i] and portfolio['holdings'][i - 1] > 0 and data['RSI'][i] > 70:
            elif sell_signal[i] and portfolio['holdings'][i-1] > 0 and last_trade_price < data['Close'][i] and data['RSI'][i] > 70:
                portfolio['cash'][i] = portfolio['holdings'][i-1] * data['Close'][i]
                portfolio['holdings'][i] = 0
                portfolio['trades'][i] = portfolio['trades'][i-1] + 1
                btc_amount = portfolio['holdings'][i-1]
                trade_log.append({
                    'Date': data.index[i],
                    'Action': 'Sell',
                    'Price': data['Close'][i],
                    'BTC_Amount': btc_amount,
                    'Cash_Gained': btc_amount * data['Close'][i],
                    'RSI': data['RSI'][i],  # Record RSI value at the time of trade
                    'Support': support,
                    'Resistance': resistance
                })
                trade_dates.append(data.index[i])  # Record trade date
                last_trade_price = data['Close'][i]
            else:
                portfolio['holdings'][i] = portfolio['holdings'][i-1]
                portfolio['cash'][i] = portfolio['cash'][i-1]
        else:
            portfolio['trades'][i] = 0  # Reset trade counter weekly


        #portfolio['cash'][i] = max(portfolio['cash'][i], portfolio['cash'][i-1])
        #portfolio['holdings'][i] = max(portfolio['holdings'][i], portfolio['holdings'][i-1])

    portfolio['total'] = portfolio['cash'] + portfolio['holdings'] * data['Close']

    # Convert trade log to DataFrame and save to Excel
    trade_df = pd.DataFrame(trade_log)
    trade_df.to_excel('./trade_log.xlsx', index=False)

    return portfolio, trade_log

# Backtesting loop
initial_capital = 100  # Define initial capital
results = [] # To store the results of each backtest

# The last date in the data
last_date = btc_data.index[-1]

# Loop for backtesting with a 12-month window, offset by 2 months each iteration
for month_offset in range(0, 60, 1):  # 60 months in 5 years
    start_date = btc_data.index[0] + pd.DateOffset(months=month_offset)
    #end_date = start_date + pd.DateOffset(months=24) # 24 months
    end_date = last_date  # Set end date to the last date in the data

    # Filter the data for the current 12-month period
    current_data = btc_data[(btc_data.index >= start_date) & (btc_data.index < end_date)]

    if len(current_data) > 0:
        portfolio, trade_log = trading_strategy(current_data, initial_capital)
        final_portfolio_value = portfolio['total'].iloc[-1]
        results.append((start_date, end_date, final_portfolio_value, trade_log))

# Print results and trade logs
for result in results:
    print(f"Backtest from {result[0].date()} to {result[1].date()}")
    print("Trade Log:")
    for trade in result[3]:
        print(trade)
    print(f"Final Portfolio Value: {result[2]}\n")

