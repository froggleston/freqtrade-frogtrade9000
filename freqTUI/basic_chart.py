#!/usr/bin/env python3

# -*- coding: utf-8 -*-

import os
import sys

from asciichart import plot, plot_str

import numpy as np
import pandas as pd
import math

# -----------------------------------------------------------------------------

this_folder = os.path.dirname(os.path.abspath(__file__))
root_folder = os.path.dirname(os.path.dirname(this_folder))
sys.path.append(root_folder + '/python')
sys.path.append(this_folder)

# -----------------------------------------------------------------------------

import ccxt  # noqa: E402

# -----------------------------------------------------------------------------

symbols = ['┼', '┤', '╶', '╴', '─', '└', '┌', '┐', '┘', '│']

class BasicCharts():
    
    def __init__(self, exchange=ccxt.binance(), symbol="BTC/USDT", timeframe="5m", limit=24, index=4):
        self.exchange = exchange
        self.symbol = symbol
        self.timeframe = timeframe
        self.limit = limit
        self.index = index

    def set_symbol(self, symbol="BTC/USDT"):
        self.symbol = symbol
        
    def set_limit(self, limit=100):
        self.limit = limit

    def set_timeframe(self, timeframe="5m"):
        if timeframe in ["1m", "5m", "15m", "1h", "4h"]:
            self.timeframe = timeframe
        
    def get_timeframe(self):
        return self.timeframe
        
    def get_ohlcv(self, timeframe=None, limit=None):
        if timeframe is not None:
            return self.exchange.fetch_ohlcv(symbol=self.symbol, timeframe=timeframe, limit=limit)
        else:
            return self.exchange.fetch_ohlcv(symbol=self.symbol, timeframe=self.timeframe, limit=self.limit)

    def prep_ohlcv(self, ohlcv):
        df = pd.DataFrame(ohlcv, columns=['date', 'Open', 'High', 'Low', 'Close', 'Volume'])
        df['date'] = pd.to_datetime(df['date'], unit = 'ms', utc=True)

        df.set_index('date', inplace=True)
        df['Close'] = df['Close'].apply(float)
        return df

    def get_chart_arr(self, height=20, basic_symbols=False):
        # get a list of ohlcv candles
        ohlcv = self.get_ohlcv(limit=self.limit)

        # get the ohlcv (closing price, index == 4)
        series = [x[self.index] for x in ohlcv]

        cfg = {'height': height}
        
        if basic_symbols:
            cfg['symbols'] = symbols
            
        # print the chart
        return plot(series, cfg)  # return chart array

    def get_chart_str(self, height=20, width=120, trades=None, basic_symbols=False):
        # get a list of ohlcv candles
        ohlcv = self.get_ohlcv(limit=self.limit)
        
        # get the ohlcv (closing price, index == 4)
        series = [x[self.index] for x in ohlcv]
        
        cfg = {'height': height}
        
        if basic_symbols:
            cfg['symbols'] = symbols
        
        outstr = plot_str(plot(series, cfg))

        return outstr

    def get_profit_str(self, trades, height=20, width=120, basic_symbols=False):
        profit = 0
        profitseries = [0]
        
        for x in trades:
            profit = profit + int(x['close_profit_abs'])
            profitseries.append(profit)
        
        cfg = {'height': height, 'min': min(profitseries)}
        
        if basic_symbols:
            cfg['symbols'] = symbols
                
        # print the chart
        outstr = plot_str(plot(profitseries[-self.limit:], cfg))
        
        return outstr
    
    def print_chart(self):
        print(self.get_chart_str())
    
def main():
    btcgbp_charts = BasicCharts(symbol="BTC/GBP")
    btcgbp_charts.combo_chart()

if __name__ == "__main__":
    main()
