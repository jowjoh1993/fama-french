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

import os
import pandas as pd
import time
import math
import quandl
import statsmodels.api as sm
from SchemaUtils import SchemaUtils
from DBUpdgradeScript import DBUpgradeScript
from td.exceptions import NotFndError

#%%####################### Define constants ###################################

# Change root_dir to the directory you which you downloaded the project
root_dir = os.path.abspath("")

# Maximum number of NaNs allowed in price history
nan_limit = 10

# List the data to keep after the GET calls
keys_to_keep=["symbol","marketCap","bookValuePerShare","sharesOutstanding"]


#%%####################### Function definitions ###############################

# Make GET requests to the TD Ameritrade API for fundamental data
# Inputs
#    symbol : symbol of the stock whose data you want, e.g. "GOOG"
#    access_token: OAuth2 access token for API authentication
# Outputs
#    JSON object containing fundamental data for the stock
def get_fundamentals(symbol,td_client):
    
    print("Getting fundamental data for "+symbol+"...")
  
    response = td_client.search_instruments(symbol=symbol,projection='fundamental')

    return response
#end def

# Make GET requests to the TD Ameritrade API for price history data
# Feel free to change the default argument values if you prefer different
# periods or frequencies for your data, or just call the function with
# different arguments.
# IMPORTANT: If you change the frequency to something other than "daily", you
# must also change the calculation of the risk free return in the "Calculate
# returns" section below to match.

def get_prices(symbol,
               td_client,                
               periodType = "year",
               period = 1,
               frequencyType = "daily",
               frequency = 1,
               ):
    
    print("Getting price data for "+symbol+"...")
    try:
        response=td_client.get_price_history(symbol=symbol,
                                         period_type=periodType,
                                         period=period,
                                         frequency_type=frequencyType,
                                         frequency=frequency
                                        )
    except NotFndError:
        print("Price data not found... continue")
        return
    return response
#end def

# Converts 'milliseconds since epoch' to 'YYYY-MM-DD'
def epoch_to_datetime(epoch_time):
    return time.strftime('%Y-%m-%d', time.localtime(epoch_time/1000))
#end def
    
# Subsets the historical price data returned from API calls
def slice_price_data(symbol,data):
    data = data['candles']
    df = pd.DataFrame(data)[['close','datetime']]
    df['datetime'] = df['datetime'].apply(epoch_to_datetime)
    df = df.rename(columns={'close':symbol,'datetime':'date'})
    df = df.set_index('date')
    return df
#end def

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
    
def read_file(filepath, split=False):
    with open(filepath,"r") as f:
        if split == False:
            return f.read()
        else:
            return f.read().splitlines()
        #end if
    #end with
#end def


#%%#################### Construct Portfolios ##################################

schema = SchemaUtils()
fundamentals=schema.executeSelectStatment('fundamentals')

# If values are zero, we don't care about them
subFund = fundamentals[abs(fundamentals.bookToMarket) > 0.00001]
subFund = subFund[subFund.marketCap > 0.0001]

# Get percentiles for determining Fama-French portfolios
n = subFund.shape[0]
pc10 = math.floor(n/10)
pc30 = pc10 * 3
pc70 = pc10 * 7
pc90 = pc10 * 9

# Sort by Book to Market Ratio, construct growth, neutral, and value portfolios
bm = subFund.sort_values('bookToMarket')
growth = bm.iloc[0:pc30]
neutral = bm.iloc[pc30:pc70]
value = bm.iloc[pc70:n]

# Sort by market cap, construct small and big portfolios
mc = subFund.sort_values('marketCap')
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

upgrade = DBUpgradeScript()
td_client = upgrade.login()        
sector_list = schema.getSectorList()
firstPrices = True
for sector in sector_list:
    price = schema.executeSelectStatment(sector)
    if firstPrices:
        prices = price
    else:
        prices = pd.merge(prices, price, how='outer',left_index=True,
                              right_index=True)     

# Get prices for value-weighted Fama-French portfolios
prices['sg'] = get_portfolio_prices(sg, prices)
prices['sn'] = get_portfolio_prices(sn, prices)  
prices['sv'] = get_portfolio_prices(sv, prices)
prices['bg'] = get_portfolio_prices(bg, prices)
prices['bn'] = get_portfolio_prices(bn, prices)
prices['bv'] = get_portfolio_prices(bv, prices)

# Get the market portfolio price (NASDAQ + NYSE + XMI)
nasdaq = upgrade.slice_price_data("NDX",upgrade.get_prices("NDX",td_client))
prices = pd.merge(prices,nasdaq,how='outer',left_index=True,right_index=True)

nyse = slice_price_data("NYA",get_prices("NYA",td_client))
prices = pd.merge(prices,nyse,how='outer',left_index=True,right_index=True)

xmi = slice_price_data("XMI",get_prices("XMI",td_client))
prices = pd.merge(prices,xmi,how='outer',left_index=True,right_index=True)

prices['market']=prices['NDX']+prices['NYA']+prices['XMI']



#%%####################### Calculate returns ##################################

# Calculate returns
returns = prices.pct_change()
returns = returns.drop(returns.index[0]) #First row is always NaN, just drop

# Get the daily risk-free rate of return
tbill = quandl.get("USTREASURY/BILLRATES", authtoken=QUANDL_TOKEN).tail(250)
tbill = tbill[['52 Wk Bank Discount Rate']]
tbill = tbill.rename(columns={'52 Wk Bank Discount Rate':'riskFreeRate'})
tbill['riskFreeRate'] = (tbill['riskFreeRate'] / 100).apply(yearly_to_daily)

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

k=1
for sym in prices.columns:
    if sym in returns.columns:
        y = returns[sym]
        try:
           model = sm.OLS(y,X).fit()
        except ValueError:  #raised if `y` is empty.
           break
        paramdict = model.params.to_dict()
        paramdict['symbol'] = sym
        paramdict['rsquared'] = model.rsquared
        df = pd.DataFrame(paramdict, index=[k-1])
        if k == 1:
            params = df
        else:
            params = params.append(df)
        #end if
        k = k + 1
    #end if
#end for

try:
    if val is None: # The variable
        print('It is None')
except NameError:
    print ("This variable is not defined")
else:
   params = params.rename(columns={'excess_return':'beta_market','SMB':'beta_smb',
                                'HML':'beta_hml','const':'alpha'})
   params = params.sort_values(by='alpha',ascending=False)

   # Print out stocks with the highest alpha, sort by descending rsquared
   print(params.head(50).sort_values(by='rsquared',ascending=False))
