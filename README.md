# FreeQuant 
[![forthebadge](https://forthebadge.com/images/badges/made-with-javascript.svg)](https://forthebadge.com)

Program to optimize and receive valuable information about your strategy. Eventually will be used as the framework for a live trading bot. Just a cute little summer project.

## Features
- Multi-parameter optimization
- Multi-MM (money management integration) : default = static type, 0.03, 3.0% position sizing
- Multi-RM (risk management integration) : default = dynamic ATR based with "move to breakeven" logic

## To-Do
- Multi-strategy library integration (break into modular components)
- OOS/IS back-testing
- Plot best iteration of parameters
- Dynamic money management position sizing based on performance/drawdown
- Statistical models to determine if a strategy has any predictive value
- live trading

### Dependencies
- [Backtrader](https://www.backtrader.com/docu/induse/)