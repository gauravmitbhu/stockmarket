from backtesting import Backtest, Strategy
from backtesting.lib import crossover

from backtesting.test import SMA, GOOG
import pandas as pd


class SmaCross(Strategy):
    n1 = 10
    n2 = 20

    def init(self):
        close = self.data.Close
        self.sma1 = self.I(SMA, close, self.n1)
        self.sma2 = self.I(SMA, close, self.n2)

    def next(self):
        if crossover(self.sma1, self.sma2):
            self.buy()
        elif crossover(self.sma2, self.sma1):
            self.sell()


excel_file_path = 'bitcoin_data_5yr.xlsx'
btc_data = pd.read_excel(excel_file_path, index_col=0, parse_dates=True)

# bt = Backtest(GOOG, SmaCross,
#               cash=10000, commission=.002,
#               exclusive_orders=True)

bt = Backtest(btc_data, SmaCross,
              cash=10000, commission=.002,
              exclusive_orders=True)

output = bt.run()
bt.plot()