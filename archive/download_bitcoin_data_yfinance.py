import pandas as pd
import yfinance as yf

# Define the cryptocurrency ticker
crypto_ticker = 'BTC-USD'  # Bitcoin ticker in Yahoo Finance

# # Downloading the data from Yahoo Finance for the last 60 days with 1-hour intervals
# btc_data = yf.download(crypto_ticker, period="60d", interval="1h")
#
# # Convert timezone-aware datetime to timezone-naive
# btc_data.index = btc_data.index.tz_localize(None)
#
# # Saving the data to an Excel file
# btc_data.to_excel('BTC-USD_data_60d_1h.xlsx')


# Specify the start and end dates
start_date = '2022-03-28'
end_date = '2022-06-20'  # 60 days from the start date

# Downloading the data from Yahoo Finance
btc_data = yf.download(crypto_ticker, start=start_date, end=end_date, interval='1h')

# Convert index to timezone-naive datetime
btc_data.index = btc_data.index.tz_localize(None)

# Saving the data to an Excel file
btc_data.to_excel('BTC-USD_data_60d_1h_bear_2022-03-28.xlsx')

# Display the first few rows of the data
print(btc_data.head())
