from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import datetime
import os.path
import time
import sys
import math


import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.indicators as btind
import backtrader.analyzers as btanalyzers
import backtrader.feeds as btfeeds
import backtrader.strategies as btstrats

import pandas

# class maxRiskSizer(bt.Sizer):
#     '''
#     Returns the number of shares rounded down that can be purchased for the
#     max rish tolerance
#     '''
#     params = (('risk', 0.03),)

#     def __init__(self):
#         if self.p.risk > 1 or self.p.risk < 0:
#             raise ValueError('The risk parameter is a percentage which must be'
#                 'entered as a float. e.g. 0.5')

#     def _getsizing(self, comminfo, cash, data, isbuy):
#         if isbuy == True:
#             size = math.floor((cash * self.p.risk) / data[0])
#         else:
#             size = math.floor((cash * self.p.risk) / data[0]) * -1
#         return size

class MyStrategy(bt.Strategy):
    params = (('period', 15),('baseline', 30),('atrperiod', 14),('atrtp', 1),('atrsl', 1.5), ('trailperc', 0.03))

    def log(self, txt, dt=None):
        ''' Logging function fot this strategy'''
        dt = dt or self.data.datetime[0]
        if isinstance(dt, float):
            dt = bt.num2date(dt)
        print('%s, %s' % (dt.isoformat(), txt))

    #strategy visualization
    def __init__(self): 

        self.dataclose = self.datas[0].close
        # SimpleMovingAverage on main data
        # Equivalent to -> sma = btind.SMA(self.data, period=self.p.period)
        self.sma = btind.MovingAverageSimple(period=self.params.baseline)
        #ATR
        self.atr = btind.AverageTrueRange(period = self.params.atrperiod)
       
        # CrossOver (1: up, -1: down) close / sma
        williams = btind.WilliamsR(period = self.params.period)
        self.overline = btind.CrossUp(williams, -20, plot=True)  
        self.belowline = btind.CrossDown(williams, -80, plot =True)
        # self.buysell = btind.CrossOver(williams, -50.0, plot =True)

    #strategy entry/exit rules and money management
    def next(self):

        abovesma = self.dataclose > self.sma[0]
        # self.log('DrawDown: %.2f' % self.stats.drawdown.drawdown[-1])
        # self.log('MaxDrawDown: %.2f' % self.stats.drawdown.maxdrawdown[-1])

        #Buy and Sell strategy conditiions
        self.buy_condition = abovesma and self.overline
        self.sell_condition = (not abovesma) and self.belowline     


        #not in a position
        if not self.position:

            if self.buy_condition:

                sdistb = self.atr[0] * self.params.atrsl
                self.sstoplevelb = self.data.close[0] + sdistb

                pdistb = self.atr[0] * self.params.atrtp
                self.ptakelevelb = self.data.close[0] - pdistb

               # self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.mainb = self.buy(size=10, exectype=bt.Order.Market)
                self.sell(size=5, exectype=bt.Order.Limit, price=self.ptakelevelb)
                self.orderb = self.sell(size=10, exectype=bt.Order.Stop, price=self.sstoplevelb)

            if self.sell_condition:
               
                sdists = self.atr[0] * self.params.atrsl
                self.sstoplevels = self.data.close[0] - sdists

                pdists = self.atr[0] * self.params.atrtp
                self.ptakelevels = self.data.close[0] + pdists

               # self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.mains = self.sell(size=10, exectype=bt.Order.Market)
                self.buy(size=5, exectype=bt.Order.Limit, price=self.ptakelevels)
                self.orders = self.buy(size=10, exectype=bt.Order.Limit, price=self.sstoplevels)
               
        else:
            
            if self.position.size > 0:
                ptakelevelb = self.ptakelevelb
                if(self.datas[0].close > ptakelevelb):
                    self.cancel(self.orderb)
                    self.sell(size=5, exectype=bt.Order.StopTrail, trailpercent=self.params.trailperc)
            elif self.dataclose < 0:
                ptakelevels = self.ptakelevels
                if(self.datas[0].close < ptakelevels):
                    self.cancel(self.orders)
                    self.buy(size=5, exectype=bt.Order.StopTrail, trailpercent=self.params.trailperc)


def runstrat():
    #Retrieve time series data
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, 'BTC-USD.csv')
    data = btfeeds.YahooFinanceCSVData(dataname=datapath)
    #------------------------------------------------------   
    
    startcash = 10000

    c = bt.Cerebro(optreturn=False)

    c.adddata(data)

    c.broker.setcash(startcash)

    # c.resampledata(data, timeframe = bt.TimeFrame.Minutes, compression=5)

    c.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe_ratio')
    c.addanalyzer(btanalyzers.DrawDown, _name='dd')

    c.optstrategy(MyStrategy, period=range(10, 30), baseline=range(50, 60), atrperiod = 14, atrtp = 1.5, atrsl = 1)

    c.addobserver(bt.observers.DrawDown)
    
    # c.addstrategy(MyStrategy)
    
    # c.addsizer(maxRiskSizer)

    optimized_runs = c.run()

    final_results_list = []
    for run in optimized_runs:
        # c.plot()
        for c in run:
            
            PnL = round(c.broker.get_value() - 10000,2)
            sharpe = c.analyzers.sharpe_ratio.get_analysis()
            dd = c.analyzers.dd.get_analysis()
            final_results_list.append([c.params.period, c.params.baseline, c.params.atrsl, c.params.atrtp, dd['moneydown'] , PnL, sharpe['sharperatio']])

    sort_by_sharpe = sorted(final_results_list, key=lambda x: x[6], 
                             reverse=True)

    print("By Sharpe: ")
    print("period indicator, direction indicator, drawdown, profit, sharpe")
    for line in sort_by_sharpe[:10]:
        print(line)


if __name__ == '__main__':
    runstrat()