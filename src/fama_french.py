#%%############################################################################
# Name:     fama_french.py
# Purpose:  Use Fama-French 3-factor model to inform investments
# Author:   Joshua W. Johnstone
#
# Updates:
#   Created 21-JUL-2019
#
# Usage:
#   Change root_dir in the next cell to point to the directory where you put
#   the project files.
#
#   It is recommended that you run this file one cell at a time. Since the TD
#   Ameritrade API access token expires 30 minutes after refresh, you will not
#   have enough time to get all the fundamental data AND price history data
#   unless you refresh the token in between. See section "Refresh Token"
#
# Disclaimer:
#   This program is intended to act as a guide to inform strictly long
#   investments in corporate stocks. If you use this program to make investment
#   decisions, you understand that the market is complex, efficient, and 
#   unpredictable. You understand that using this program to inform decisions
#   in no way guarantees success nor protects you against financial losses. 
#   By using this program, you agree that you understand the risks inherent 
#   in stock market investments.

#%%######################## Import modules ####################################

import pandas as pd
import math
import nasdaqdatalink as ndl
import statsmodels.api as sm

import numpy as np
from TDA.config import QUANDL_TOKEN
from SchemaUtils import SchemaUtils
from DBUpdateScript import DBUpdateScript
import yfinance as yf


#%%####################### Define constants ###################################

# Amount of capital to invest
inv_amount = 10000

# Number of stocks to include in portfolio
N = 10

#%%####################### Function definitions ###############################

# Given a list of symbols in a portfolios, returns the price of the value-
# weighted portfolio of the symbols. For example, if list_of_symbols contains
# ["GOOG","AAPL"], returns the price of GOOG + AAPL (one share each)
def get_portfolio_prices(list_of_symbols, prices_df):
    j = 1
    x = 0
    for sym in list_of_symbols:
        if sym in prices_df.columns:
            if sym == "BRK/B":
                sym = "BRK.B"
            #end if
            if j == 1:
                x = prices_df[sym]
            else:
                x = x + prices_df[sym]
            #end if
            j = j + 1
        #end if
    #end for
    return x
#end def
    
# Get daily risk-free rate of return
def yearly_to_daily(yearly_rate):
    return (1 + yearly_rate) ** (1/360) - 1
#end def

#%%#################### Construct Portfolios ##################################

schema = SchemaUtils()
fundamentals=schema.executeSelectStatement('fundamentals',None)
#fundamentals['symbol']=fundamentals['symbol'].str.lower()
[x.lower() for x in ["A", "B", "C"]]
fundamentals['symbol']= [x.lower() for x in schema.removeKeywordsFromSymbols(fundamentals['symbol'].tolist())]

# If values are zero, we don't care about them
subFund = fundamentals[abs(fundamentals.booktomarket) > 0.00001]
subFund = subFund[subFund.marketcap > 0.0001]

# Get percentiles for determining Fama-French portfolios
n = subFund.shape[0]
pc10 = math.floor(n/10)
pc30 = pc10 * 3
pc70 = pc10 * 7
pc90 = pc10 * 9

# Sort by Book to Market Ratio, construct growth, neutral, and value portfolios
bm = subFund.sort_values('booktomarket')
growth = bm.iloc[0:pc30]
neutral = bm.iloc[pc30:pc70]
value = bm.iloc[pc70:n]

# Sort by market cap, construct small and big portfolios
mc = subFund.sort_values('marketcap')
small = mc.iloc[0:pc10]
big = mc.iloc[pc90:n]

# Create the six Fama-French portfolios
sg = pd.merge(small, growth, how='inner')['symbol']
sn = pd.merge(small, neutral, how='inner')['symbol']
sv = pd.merge(small, value, how='inner')['symbol']
bg = pd.merge(big, growth, how='inner')['symbol']
bn = pd.merge(big, neutral, how='inner')['symbol']
bv = pd.merge(big, value, how='inner')['symbol']

#%%#################### Get Prices ##################################

update = DBUpdateScript()
td_client = update.login()        
sector_list = schema.getSectorList()
firstPrices = True
for sector in sector_list:
    price = schema.executeSelectStatement(sector,'date')
    if not price.empty:
        if firstPrices:
            prices = price
            firstPrices = False
        else:
            prices = pd.merge(prices, price, how='outer',left_index=True,
                              right_index=True) 
    else:
        print('Dataset price_data.'+sector+' is empty. Rerun the DBUpdateScript to get this data.')

prices.rename(columns={'date_x':'date'},inplace = True)

# Get prices for value-weighted Fama-French portfolios
prices['sg'] = get_portfolio_prices(sg, prices)
prices['sn'] = get_portfolio_prices(sn, prices)  
prices['sv'] = get_portfolio_prices(sv, prices)
prices['bg'] = get_portfolio_prices(bg, prices)
prices['bn'] = get_portfolio_prices(bn, prices)
prices['bv'] = get_portfolio_prices(bv, prices)

today = '2022-01-07'
epoch_today = update.get_latest_date(prices, '2022-01-07')

# Get the market portfolio price (NASDAQ + NYSE + XMI)
nasdaq = yf.download("^NDX", start="2021-01-07", end="2022-01-07");
nasdaq = nasdaq[['Close']]
nasdaq = nasdaq.rename(columns={'Close':'NDX'})
prices = pd.merge(prices,nasdaq,how='outer',left_index=True,right_index=True)

nyse = yf.download("^NYA", start="2021-01-07", end="2022-01-07");
nyse = nyse[['Close']]
nyse = nyse.rename(columns={'Close':'NYA'})
prices = pd.merge(prices,nyse,how='outer',left_index=True,right_index=True)

xmi = yf.download("^XMI", start="2021-01-07", end="2022-01-07");
xmi = xmi[['Close']]
xmi = xmi.rename(columns={'Close':'XMI'})
prices = pd.merge(prices,xmi,how='outer',left_index=True,right_index=True)

prices['market']=prices['NDX']+prices['NYA']+prices['XMI']

#%%####################### Calculate returns ##################################

# Calculate returns
returns = prices.pct_change()
vol = prices.pct_change().std()*(252**0.5)
#print(vol)
vol = vol.where(vol < 0.2)
returns = returns.drop(returns.index[0]) #First row is always NaN, just drop
returns = returns.filter(items=vol.index)

# Get the daily risk-free rate of return
tbill = ndl.get("USTREASURY/BILLRATES", authtoken=QUANDL_TOKEN).tail(250)
tbill = tbill[['52 Wk Bank Discount Rate']]
tbill = tbill.rename(columns={'52 Wk Bank Discount Rate':'riskFreeRate'})

# TODO: Do we need to divide by 100 here???
tbill['riskFreeRate'] = (tbill['riskFreeRate']).apply(yearly_to_daily)

returns = pd.merge(returns,tbill,how='outer',left_index=True,right_index=True)

# Get excess return of the market over the risk-free rate
returns['excess_return'] = returns['market'] - returns['riskFreeRate']

# Calculate SMB and HML returns
returns['SMB'] = (1/3)*(returns['sg']+returns['sn']+returns['sv']) - \
                 (1/3)*(returns['bg']+returns['bn']+returns['bv'])

returns['HML'] = (1/2)*(returns['sv']+returns['bv']) - \
                 (1/2)*(returns['sg']+returns['bg'])


#%%#################### Run linear regressions ################################

# Use linear interpolation to fill missing data
returns = returns.interpolate(method='linear',limit_direction='forward',axis=0)
returns = returns.dropna()

X = returns[['excess_return', 'SMB', 'HML']]
X = sm.add_constant(X)

#Get rid of date
prices_columns = prices.columns[1:]
returns_columns = returns.columns[1:]
np.seterr(all='raise')
k=1
for sym in prices_columns:
    if sym in returns_columns:
        y = returns[sym]
        try:
           model = sm.OLS(y,X).fit()
        except ValueError as e:  #raised if `y` is empty.
            print('Invalid value!!!')
            print(e)
        paramdict = model.params.to_dict()
        paramdict['symbol'] = sym
        try:
            paramdict['rsquared'] = model.rsquared
        except FloatingPointError as e:
            print('Division by zero.. skipping ticker '+sym)
            print(e)
        paramdict['error'] = model.resid
        df = pd.DataFrame(paramdict, index=[k-1])
        if k == 1:
            params = df
        else:
            params = params.append(df)
        #end if
        k = k + 1
    #end if
#end for
    
params = params.rename(columns={'excess_return':'beta_market','SMB':'beta_smb',
                                'HML':'beta_hml','const':'alpha'})
#params = params.sort_values(by='alpha',ascending=False)

#not_in = ['market','NDX','XMI','NYA','bg','bn','bv','sg','sn','sv']
not_in = ['market','QQQ','ONEQ','DIA','bg','bn','bv','sg','sn','sv']

params=params[~params['symbol'].isin(not_in)]

#%%####################### Maximize both alpha and rsquared ##################


max_fit = params.max()['rsquared']
max_alpha = params.max()['alpha']


# Weights for optimization
w_fit = 0.0008
w_alpha = 0.9992

std = params.std()['alpha']
mean = params.mean()['alpha']

params['std_from_mean'] = round(abs(params['alpha']-mean)/std,ndigits=2)

# Drop outliers where alpha is more than 6 std from the mean

params = params[params['std_from_mean'] < 6]

# Calculate objective function

params['objective'] = w_fit*(params['rsquared']-max_fit)**2 + w_alpha*(params['alpha']-max_alpha)**2

params.to_excel('results.xlsx')

# Minimize objective function to maximize combination of alpha and rsquared
params = params.sort_values(by='objective')

shortlist = params.head(N)
print(shortlist)

   
   
#%%######################### Allocate Assets ##################################

target = inv_amount / N

allocation = {}
current_prices = {}
symbols = list(shortlist['symbol'])
shortlist = shortlist.set_index('symbol')
    
for asset in symbols:
    current_prices[asset] = list(prices[asset])[-1]
    allocation[asset] = round(target / current_prices[asset])
    
allocation = pd.DataFrame(allocation, index=['Number of Shares']).transpose()
current_prices = pd.DataFrame(current_prices, index=['Current Price']).transpose()

allocation = allocation.join(current_prices)
allocation['Subtotal'] = allocation['Number of Shares'] * allocation['Current Price']
allocation = allocation.join(shortlist[['rsquared', 'alpha']])

allocation.to_excel('allocation.xlsx')
print(allocation)
print("Total Portfolio Cost = $" + str(round(allocation.sum()['Subtotal'],2)))

