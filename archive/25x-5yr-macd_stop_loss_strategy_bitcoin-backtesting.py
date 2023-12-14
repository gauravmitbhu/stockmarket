import os
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pandas.errors import SettingWithCopyWarning

# Define the cryptocurrency symbol
crypto_symbol = "BTC-USD"

# Fetch data for the last 2 years and save to a CSV file
# btc_data = yf.download(crypto_symbol, period="2y")
# btc_data.to_csv('./bitcoin_data_2y.csv')  # Save to CSV

#csv_file_path = 'bitcoin_data_jan-022-dec-2023.csv'
#btc_data = pd.read_csv(csv_file_path, index_col=0, parse_dates=True)

excel_file_path = 'bitcoin_data_5yr.xlsx'
btc_data = pd.read_excel(excel_file_path, index_col=0, parse_dates=True)

def calculate_holding_value(data, start_date, end_date, initial_investment):
    """Calculate the value of holding an asset from start_date to end_date."""
    start_price = data.loc[start_date, 'Close']
    end_price = data.loc[end_date, 'Close']
    return initial_investment * (end_price / start_price)

def calculate_atr(data, window=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    atr = true_range.rolling(window).mean()
    return atr

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
    portfolio['total'] = portfolio['cash'] + portfolio['holdings'] * data.loc[portfolio.index, 'Close']
    monthly_portfolio_values = [initial_capital]  # Start with the initial capital

    # # Update the loop to check portfolio value at the end of each month
    # for month in range(1, 13):  # Loop through 12 months
    #     month_end = data.index.min() + pd.DateOffset(months=month)
    #     if month_end in data.index:
    #         # Update total portfolio value at the end of the month
    #         portfolio['total'] = portfolio['cash'] + portfolio['holdings'] * data.loc[month_end, 'Close']
    #         monthly_portfolio_values.append(portfolio['total'].loc[month_end])
    #     else:
    #         # If month_end isn't in the index, use the last available date
    #         last_date = data.index[data.index < month_end][-1]
    #         portfolio['total'] = portfolio['cash'] + portfolio['holdings'] * data.loc[last_date, 'Close']
    #         monthly_portfolio_values.append(portfolio['total'].loc[last_date])

    # Initialize the DataFrame to store trade details
    trade_log = []
    last_buy_price = None
    stop_loss_atr = None

    trade_dates = []  # To store the dates of trades for plotting

    last_trade_price = 999999  # To store the price of the last trade
    atr_window = 14  # or whatever your ATR window is

    for i in range(1, len(data)):
        #initialize holdings and cash
        portfolio['holdings'][i] = portfolio['holdings'][i - 1]
        portfolio['cash'][i] = portfolio['cash'][i - 1]

        # Update the total portfolio value with the current day's closing price
        portfolio['total'][i] = portfolio['cash'][i] + portfolio['holdings'][i] * data['Close'][i]

        # Calculate support and resistance up to the current date
        support, resistance = calculate_support_resistance(data, data.index[i])

        if i%30 == 0:
            monthly_portfolio_values.append(portfolio['total'].loc[data.index[i]])
            print(f"Portfolio value at {data.index[i]}: {portfolio['total'].loc[data.index[i]]}")

        if i <= atr_window:
            continue  # Skip early entries where ATR can't be calculated

        current_data_slice = data.iloc[:i + 1]
        current_atr_series = calculate_atr(current_data_slice)
        current_atr = current_atr_series.iloc[-1]
        if stop_loss_atr is not None:
            # Update stop loss price
            stop_loss_atr = last_buy_price - atr_multiplier * current_atr

        if buy_signal[i] and portfolio['cash'][i-1] > 0 and data['RSI'][i] < 45:
            last_buy_price = data['Close'][i]  # Update the last buy price
            stop_loss_atr = last_buy_price - atr_multiplier * current_atr
            portfolio['holdings'][i] = portfolio['cash'][i-1] / data['Close'][i]
            portfolio['cash'][i] = 0
            portfolio['trades'][i] = portfolio['trades'][i-1] + 1
            btc_amount = portfolio['cash'][i - 1] / data['Close'][i]
            portfolio['total'][i] = portfolio['cash'][i] + portfolio['holdings'][i] * data['Close'][i]
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
        elif sell_signal[i] and portfolio['holdings'][i-1] > 0 and last_trade_price < data['Close'][i]  and data['RSI'][i] > 65:
            last_buy_price = None  # Reset the last buy price
            stop_loss_atr = None
            portfolio['cash'][i] = portfolio['holdings'][i - 1] * data['Close'][i]
            portfolio['holdings'][i] = 0
            portfolio['trades'][i] = portfolio['trades'][i - 1] + 1
            portfolio['total'][i] = portfolio['cash'][i] + portfolio['holdings'][i] * data['Close'][i]
            btc_amount = portfolio['holdings'][i - 1]
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

        elif last_buy_price and stop_loss_atr and portfolio['holdings'][i - 1] > 0:
            # Check for stop loss
            if data['Close'][i] < stop_loss_atr:
                # Trigger stop loss
                portfolio['cash'][i] = portfolio['holdings'][i - 1] * data['Close'][i]
                portfolio['holdings'][i] = 0
                portfolio['trades'][i] = portfolio['trades'][i - 1] + 1
                portfolio['total'][i] = portfolio['cash'][i] + portfolio['holdings'][i] * data['Close'][i]
                btc_amount = portfolio['holdings'][i - 1]
                trade_log.append({
                    'Date': data.index[i],
                    'Action': 'Sell - Stop Loss',
                    'Price': data['Close'][i],
                    'BTC_Amount': btc_amount,
                    'Cash_Gained': btc_amount * data['Close'][i],
                    'RSI': data['RSI'][i],  # Record RSI value at the time of trade
                    'Support': support,
                    'Resistance': resistance
                })
                last_buy_price = None  # Reset the last buy price
                stop_loss_atr = None
                trade_dates.append(data.index[i])  # Record trade date

    portfolio['total'] = portfolio['cash'] + portfolio['holdings'] * data['Close']

    # Convert trade log to DataFrame and save to Excel
    # trade_df = pd.DataFrame(trade_log)
    # trade_df.to_excel('./trade_log.xlsx', index=False)

    return portfolio, trade_log, monthly_portfolio_values

# Suppress FutureWarnings
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)

# Backtesting loop
initial_capital = 5000  # Define initial capital
results = [] # To store the results of each backtest
#stop_loss_percent = 10  # Stop loss percentage
atr_multiplier=2
# Initialize the plot before the backtesting loop
plt.figure(figsize=(10, 5))
plt.ion()  # Turn on interactive plotting mode

# The last date in the data
last_date = btc_data.index[-1]

# Loop for backtesting with a 12-month window, offset by 2 months each iteration
# Loop for backtesting with a 12-month window, offset by 2 months each iteration
for month_offset in range(0, 60, 2):  # 60 months in 5 years
    start_date = btc_data.index[0] + pd.DateOffset(months=month_offset)
    end_date = last_date

    # Filter the data for the current backtest period
    current_data = btc_data[(btc_data.index >= start_date) & (btc_data.index <= end_date)]

    if not current_data.empty:
        portfolio, trade_log, monthly_portfolio_values = trading_strategy(current_data, initial_capital)

        final_portfolio_value = portfolio['total'].iloc[-1]

        # Calculate holding value
        holding_value = calculate_holding_value(btc_data, start_date, end_date, initial_capital)

        # Print the results immediately after each backtest run
        print(f"Backtest from {start_date.date()} to {end_date.date()}")
        print("Trade Log:")
        for trade in trade_log:
            print(trade)
        print(f"Final Portfolio Value: {final_portfolio_value}\n")
        print(f"Value if Held: {holding_value}\n")

        plt.plot(range(len(monthly_portfolio_values)), monthly_portfolio_values,
                 label=f'Backtest {month_offset // 2 + 1}')
        plt.xlabel('Month Number')
        plt.ylabel('Portfolio Value')
        plt.title('Portfolio Value over Months for Each Backtest')
        plt.legend()
        plt.draw()  # Redraw the current figure
        plt.pause(0.01)  # Pause for a short period to allow the plot to update

plt.ioff()  # Turn off interactive plotting mode
plt.show()  # Show the plot after the loop