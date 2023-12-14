import requests
import pandas as pd
import datetime
import time

# Function to fetch data from Binance API
def fetch_binance_data(symbol, interval, start_time, end_time, limit):
    url = 'https://api.binance.com/api/v3/klines'
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_time,
        'endTime': end_time,
        'limit': limit
    }
    response = requests.get(url, params=params)
    data = response.json()
    df = pd.DataFrame(data)
    df.columns = ['Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 'Close time', 'Quote asset volume', 'Number of trades', 'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore']
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df.set_index('Open time', inplace=True)
    return df

# Main function to download data in chunks
def download_data(symbol, interval, days_per_chunk, total_days_back, filename):
    all_data = pd.DataFrame()
    end_time = datetime.datetime.now()
    for _ in range(total_days_back // days_per_chunk):
        start_time = end_time - datetime.timedelta(days=days_per_chunk)
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        data_chunk = fetch_binance_data(symbol, interval, start_timestamp, end_timestamp, 1000)
        all_data = pd.concat([data_chunk, all_data])
        end_time = start_time
        print(f'Downloaded {days_per_chunk} days of data from {start_time} to {end_time}')
        time.sleep(2)  # Pause to avoid hitting rate limits
    all_data.to_excel(filename)
    return all_data

# Example usage 1 - download 5 years of 15 minute data for BTCUSDT
# symbol = 'BTCUSDT'
# interval = '15m'
# days_per_chunk = 60
# total_days_back = 5 * 365  # 5 years
# filename = 'BTCUSDT_5_years_data.xlsx'
# download_data(symbol, interval, days_per_chunk, total_days_back, filename)

# Example usage 2 - download 5 years of 1 hour data for BTCUSDT
symbol = 'BTCUSDT'
interval = '1h'
days_per_chunk = 60
total_days_back = 120  # 5 years
filename = 'BTCUSDT_5_years_data_1h.xlsx'
download_data(symbol, interval, days_per_chunk, total_days_back, filename)
