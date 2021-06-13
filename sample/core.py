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

class maxRiskSizer(bt.Sizer):
    '''
    Returns the number of shares rounded down that can be purchased for the
    max rish tolerance
    '''
    params = (('risk', 0.03),)

    def __init__(self):
        if self.p.risk > 1 or self.p.risk < 0:
            raise ValueError('The risk parameter is a percentage which must be'
                'entered as a float. e.g. 0.5')

    def _getsizing(self, comminfo, cash, data, isbuy):
        if isbuy == True:
            size = math.floor((cash * self.p.risk) / data[0])
        else:
            size = math.floor((cash * self.p.risk) / data[0]) * -1
        return size

class MyStrategy(bt.Strategy):
    params = (('period', 15),('baseline', 30),('atrperiod', 14),('atrtp', 1),('atrsl', 1.5))

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
        self.sma = btind.MovingAverageSimple(self.dataclose, period=self.params.baseline)

        #ATR
        self.atr = btind.AverageTrueRange(period = self.params.atrperiod)
       

        # CrossOver (1: up, -1: down) close / sma
        williams = btind.WilliamsR(period = self.params.period)
        self.overline = btind.CrossUp(williams, -20, plot=True) 
        self.belowline = btind.CrossDown(williams, -80, plot =True)
        # self.buysell = btind.CrossOver(williams, -50.0, plot =True)

        # Sentinel to None: new ordersa allowed
        self.order = None

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

                self.entryB = self.dataclose

               #ATR calculations
                self.sdist = self.atr[0] * self.params.atrsl
                self.sstop = self.dataclose - self.sdist

                self.pdist = self.atr[0] * self.params.atrtp
                self.ptake = self.dataclose + self.pdist
                
               # self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.mainb = self.buy(exectype=bt.Order.Market)

            if self.sell_condition:

                self.entryS = self.dataclose
                #ATR calculations
                self.sdist = self.atr[0] * self.params.atrsl
                self.sstop = self.dataclose + self.sdist

                self.pdist = self.atr[0] * self.params.atrtp
                self.ptake = self.dataclose - self.pdist

               # self.log('SELL CREATE, %.2f' % self.data.close[0])
                self.mains = self.sell(exectype=bt.Order.Market)

        #in a position
        else:
            #in a long?
            if self.position.size > 0:

                #Trailing Stop for a buy order
                if self.dataclose < self.sstop:
                    self.sell(exectype=bt.Order.Stop, parent = self.mainb)
                else:
                   # Update only if greater than
                   self.sstop = max(self.sstop, self.dataclose - self.sdist)

                #take profit logic   
                if self.dataclose < self.ptake:
                    self.sell(size = self.position.size*0.5, exectype=bt.Order.Limit, parent = self.mainb)
                    self.sstop = self.entryB + self.atr[0]
                else:
                    self.ptake = max(self.ptake, self.dataclose + self.pdist)

            #in a short?
            if self.position.size < 0:

                #Trailing Stop for a sell order
                if self.dataclose > self.sstop:
                   self.buy(exectype=bt.Order.Stop, parent = self.mains)
                else:
                    # Update only if greater than
                  self.sstop = max(self.sstop, self.dataclose + self.sdist)
                
                #take profit logic
                if self.dataclose < self.ptake:
                    self.buy(size = self.position.size * 0.5, exectype=bt.Order.Limit, parent = self.mains)
                    self.sstop = self.entryS - self.atr[0]
                else:
                    self.ptake = max(self.ptake, self.dataclose + self.pdist)
         

    
def runstrat():

    #Retrieve time series data
    modpath = os.path.dirname(os.path.abspath(sys.argv[0]))
    datapath = os.path.join(modpath, '../BTC-USD.csv')
    data = btfeeds.YahooFinanceCSVData(dataname=datapath)
    #------------------------------------------------------   
    
    startcash = 10000

    c = bt.Cerebro(optreturn=False)

    c.adddata(data)

    c.broker.setcash(startcash)

    # c.resampledata(data, timeframe = bt.TimeFrame.Minutes, compression=5)

    c.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe_ratio')
    c.addanalyzer(btanalyzers.DrawDown, _name='dd')

    c.optstrategy(MyStrategy, period=range(5, 30), baseline=range(30, 70), atrperiod = 14, atrtp = range(1, 3), atrsl = range(1, 3))

    c.addobserver(bt.observers.DrawDown)
    
    # c.addstrategy(MyStrategy)
    
    c.addsizer(maxRiskSizer)

    optimized_runs = c.run()

    final_results_list = []
    for run in optimized_runs:
        for strategy in run:
            PnL = round(strategy.broker.get_value() - 10000,2)
            sharpe = strategy.analyzers.sharpe_ratio.get_analysis()
            dd = strategy.analyzers.dd.get_analysis()
            final_results_list.append([strategy.params.period, strategy.params.baseline, strategy.params.atrsl, strategy.params.atrtp, dd['moneydown'] , PnL, sharpe['sharperatio']])

    sort_by_sharpe = sorted(final_results_list, key=lambda x: x[6], 
                             reverse=True)

    print("By Sharpe: ")
    print("period indicator, direction indicator, drawdown, profit, sharpe")
    for line in sort_by_sharpe[:10]:
        print(line)

    # c.plot()

if __name__ == '__main__':
    runstrat()