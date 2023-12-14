import requests
import pandas as pd
import datetime

# Function to fetch data from Binance API
def fetch_binance_data(symbol, interval, total_days_back, filename):
    url = 'https://api.binance.com/api/v3/klines'

    # Calculate start and end times
    end_time = datetime.datetime.now()
    start_time = end_time - datetime.timedelta(days=total_days_back)
    start_timestamp = int(start_time.timestamp() * 1000)
    end_timestamp = int(end_time.timestamp() * 1000)

    # Define request parameters
    params = {
        'symbol': symbol,
        'interval': interval,
        'startTime': start_timestamp,
        'endTime': end_timestamp,
        'limit': 1000  # Max limit
    }

    # Fetch data from Binance API
    response = requests.get(url, params=params)
    data = response.json()

    # Create DataFrame and format columns
    df = pd.DataFrame(data, columns=[
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume',
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ])
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df['Close time'] = pd.to_datetime(df['Close time'], unit='ms')
    df.set_index('Open time', inplace=True)

    # Save to Excel
    df.to_excel(filename)
    print(f"Data saved to {filename}")

    return df

# Example usage - download 60 days of 1 hour data for BTCUSDT
symbol = 'BTCUSDT'
interval = '1h'
total_days_back = 60  # 60 days
filename = 'BTCUSDT_60_days_data_1h.xlsx'
fetch_binance_data(symbol, interval, total_days_back, filename)
