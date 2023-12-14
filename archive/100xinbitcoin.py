import os
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Define the cryptocurrency symbol
crypto_symbol = "BTC-USD"

# Fetch data for the last 2 years and save to a CSV file
btc_data = yf.download(crypto_symbol, period="2y")
btc_data.to_csv('./bitcoin_data_2y.csv')  # Save to CSV

def compute_rsi(data, window=14):
    delta = data.diff()
    up, down = delta.clip(lower=0), -1 * delta.clip(upper=0)
    roll_up = up.rolling(window).mean()
    roll_down = down.rolling(window).mean()
    rs = roll_up / roll_down
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_atr(data, window=14):
    high_low = data['High'] - data['Low']
    high_close = np.abs(data['High'] - data['Close'].shift())
    low_close = np.abs(data['Low'] - data['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(window).mean()

def trading_strategy(data, initial_capital):
    # Calculate MACD and Signal Line indicators
    exp1 = data['Close'].ewm(span=12, adjust=False).mean()
    exp2 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp1 - exp2
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # Calculate RSI
    data['RSI'] = compute_rsi(data['Close'])

    # Generate signals
    buy_signal = (data['MACD'] > data['Signal_Line']) & (data['RSI'] < 70)
    sell_signal = (data['MACD'] < data['Signal_Line']) & (data['RSI'] > 30)

    # Calculate ATR for volatility
    data['ATR'] = compute_atr(data)

    # Initialize portfolio
    portfolio = pd.DataFrame(index=data.index)
    portfolio['holdings'] = np.zeros(len(data))
    portfolio['cash'] = np.zeros(len(data))
    portfolio['cash'][0] = initial_capital
    portfolio['trades'] = 0  # Counter for trades

    # Initialize the DataFrame to store trade details
    trade_log = []

    for i in range(1, len(data)):
        # Limit to two trades per week
        if portfolio['trades'][i-1] < 2:
            if buy_signal[i] and portfolio['cash'][i-1] > 0:
                portfolio['holdings'][i] = portfolio['cash'][i-1] / data['Close'][i]
                portfolio['cash'][i] = 0
                portfolio['trades'][i] = portfolio['trades'][i-1] + 1
                btc_amount = portfolio['cash'][i - 1] / data['Close'][i]
                trade_log.append({
                    'Date': data.index[i],
                    'Action': 'Buy',
                    'Price': data['Close'][i],
                    'BTC_Amount': btc_amount,
                    'Cash_Used': portfolio['cash'][i - 1]
                })
            elif sell_signal[i] and portfolio['holdings'][i-1] > 0:
                portfolio['cash'][i] = portfolio['holdings'][i-1] * data['Close'][i]
                portfolio['holdings'][i] = 0
                portfolio['trades'][i] = portfolio['trades'][i-1] + 1
                btc_amount = portfolio['holdings'][i-1]
                trade_log.append({
                    'Date': data.index[i],
                    'Action': 'Sell',
                    'Price': data['Close'][i],
                    'BTC_Amount': btc_amount,
                    'Cash_Gained': btc_amount * data['Close'][i]
                })
        else:
            portfolio['trades'][i] = 0  # Reset trade counter weekly

        portfolio['cash'][i] = max(portfolio['cash'][i], portfolio['cash'][i-1])
        portfolio['holdings'][i] = max(portfolio['holdings'][i], portfolio['holdings'][i-1])

    portfolio['total'] = portfolio['cash'] + portfolio['holdings'] * data['Close']

    # Convert trade log to DataFrame and save to Excel
    trade_df = pd.DataFrame(trade_log)
    trade_df.to_excel('./trade_log.xlsx', index=False)

    return portfolio

initial_capital = 100  # 100 euros
investment_portfolio = trading_strategy(btc_data, initial_capital)

# Plotting the data and investment
plt.figure(figsize=(12, 18))

# Subplot for Close Price
plt.subplot(3, 1, 1)
plt.plot(btc_data['Close'], label='Bitcoin Close Price', color='orange')
plt.title('Bitcoin Close Price')
plt.ylabel('Price (USD)')
plt.legend()

# Subplot for Volume
plt.subplot(3, 1, 2)
plt.bar(btc_data.index, btc_data['Volume'], label='Bitcoin Volume', color='blue')
plt.ylabel('Volume')
plt.legend()

# Subplot for Investment
plt.subplot(3, 1, 3)
# Aggregate total value by month
monthly_investment = investment_portfolio['total'].resample('M').last()
plt.plot(monthly_investment.index, monthly_investment, label='Monthly Investment Value', color='green')
plt.title('Monthly Investment Value Over Time')
plt.xlabel('Date')
plt.ylabel('Value (EUR)')
plt.legend()

plt.tight_layout()
plt.show()
