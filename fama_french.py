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

#%%####################### Define constants ###################################

# Change root_dir to the directory you which you downloaded the project
root_dir = r"C:\Users\joshj\Desktop\algo"

# Maximum number of NaNs allowed in price history
nan_limit = 10

# List the data to keep after the GET calls
keys_to_keep=["symbol","marketCap","bookValuePerShare","sharesOutstanding"]


#%%######################## Import modules ####################################

import json
import requests
import pandas as pd
import time
import math
import quandl
import statsmodels.api as sm

#%%####################### Function definitions ###############################

# Make GET requests to the TD Ameritrade API for fundamental data
# Inputs
#    symbol : symbol of the stock whose data you want, e.g. "GOOG"
#    access_token: OAuth2 access token for API authentication
# Outputs
#    JSON object containing fundamental data for the stock
def get_fundamentals(symbol, access_token):
    headers = {"Authorization": "Bearer " + access_token}
    url = "https://api.tdameritrade.com/v1/instruments" 
    url = url + "?symbol=" + symbol + "&projection=fundamental"
    print("Getting fundamental data for " + symbol + "...")
    response = requests.get(url, headers=headers)
    print(response)
    me_json = response.json()
    return me_json
#end def

# Make GET requests to the TD Ameritrade API for price history data
# Feel free to change the default argument values if you prefer different
# periods or frequencies for your data, or just call the function with
# different arguments.
# IMPORTANT: If you change the frequency to something other than "daily", you
# must also change the calculation of the risk free return in the "Calculate
# returns" section below to match.
def get_prices(symbol, 
               access_token, 
               periodType = "year",
               period = 1,
               frequencyType = "daily",
               frequency = 1
               ):
    headers = {"Authorization": "Bearer " + access_token}
    url = "https://api.tdameritrade.com/v1/marketdata/"+symbol+"/pricehistory"
    url = url + "?periodType="+periodType
    url = url + "&period="+str(period)
    url = url + "&frequencyType="+frequencyType
    url = url + "&frequency="+str(frequency)
    print("Getting price data for " + symbol + "...")
    response = requests.get(url, headers=headers)
    print(response)
    me_json = response.json()
    return me_json
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

#%%############################# Read files ###################################

# Read client ID for TD Ameritrade app
client_id = read_file(root_dir + r"\TDA\client_id.txt")

# Read the access token for API authentication
token = read_file(root_dir + r"\TDA\access_token.txt")

# Read the list of assets to include in the model
symbol_list = read_file(root_dir + r"\asset_universe.txt", split=True)

# Read the Quandle auth token
authtoken = read_file(root_dir + r"\quandl_authtoken.txt")


#%%#################### Get fundamental data ##################################

# Initialize the data frame to hold fundamental data
fundamentals = pd.DataFrame()

for sym in symbol_list:
    # Call get_fundamentals and convert JSON to dictionary
    temp = get_fundamentals(sym, token)
    if sym in temp.keys():
        dictionary = eval(json.dumps(temp))[sym]['fundamental']
    
        # Subset to only keep data specified in keys_to_keep
        dictionary = {key: dictionary[key] for key in keys_to_keep}
        
        # Append dictionary to the data frame
        fundamentals = fundamentals.append([dictionary])
    else:
        print("WARNING: " + sym + " is an invalid stock ticker symbol!")
    #end if
    
    # TD has a limit of 2 API calls per second, so throttle back the speed
    time.sleep(0.3)
#end for

# Calculate book-to-market ratio
fundamentals['equity'] = fundamentals['bookValuePerShare'] * \
                         fundamentals['sharesOutstanding']
fundamentals['bookToMarket']=fundamentals['equity'] / fundamentals['marketCap']


#%%#################### Construct Portfolios ##################################

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

#%%#################### Refresh access token ##################################

# TD Ameritrade's API access tokens expire after just 30 minutes. Is is 
# recommended that, at this point in the program, you return to an internet
# browser and refresh the token at the following address:

# https://developer.tdameritrade.com/authentication/apis/post/token-0

# I have not yet been able to get the POST call for this action to work
# successfully from Python. Unless you can figure this part out, you'll just
# have to run the POST from the browser.

# Once you refresh the token, make sure to update it in the access_token.txt
# file, save the file, and re-read the file by running this line of code:

token = read_file(root_dir + r"\TDA\access_token.txt")

#%%####################### Get price history ##################################

# Get the historical stock prices for symbols in symbol_list
j = 1
for sym in symbol_list:
    result = get_prices(sym,token)
    if result['empty'] == False:
        df = slice_price_data(sym,result)
        if j == 1:
            prices = df
            j = j + 1
        else:
            prices = pd.merge(prices, df, how='outer',left_index=True,
                               right_index=True)
        #end if
    else:
        print("WARNING: " + sym + " is an invalid stock ticker symbol!")
    #end if
    time.sleep(0.3) # As before, can't make too many API requests per second
#end for

# Drop any column with too much missing data
for col in prices.columns:
    if prices[col].isna().sum() > nan_limit:
        print("WARNING: NaN limit exceeded! Dropping " + col + ".")
        prices = prices.drop(columns=[col])
    #end if
#end for

# Get prices for value-weighted Fama-French portfolios
prices['sg'] = get_portfolio_prices(sg, prices)
prices['sn'] = get_portfolio_prices(sn, prices)  
prices['sv'] = get_portfolio_prices(sv, prices)
prices['bg'] = get_portfolio_prices(bg, prices)
prices['bn'] = get_portfolio_prices(bn, prices)
prices['bv'] = get_portfolio_prices(bv, prices)

# Get the market portfolio price (NASDAQ + NYSE + XMI)
nasdaq = slice_price_data("NDX",get_prices("NDX",token))
prices = pd.merge(prices,nasdaq,how='outer',left_index=True,right_index=True)

nyse = slice_price_data("NYA",get_prices("NYA",token))
prices = pd.merge(prices,nyse,how='outer',left_index=True,right_index=True)

xmi = slice_price_data("XMI",get_prices("XMI",token))
prices = pd.merge(prices,xmi,how='outer',left_index=True,right_index=True)

prices['market']=prices['NDX']+prices['NYA']+prices['XMI']



#%%####################### Calculate returns ##################################

# Calculate returns
returns = prices.pct_change()
returns = returns.drop(returns.index[0]) #First row is always NaN, just drop

# Get the daily risk-free rate of return
tbill = quandl.get("USTREASURY/BILLRATES", authtoken=authtoken).tail(250)
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
for sym in symbol_list:
    if sym in returns.columns:
        y = returns[sym]
        model = sm.OLS(y,X).fit()
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

params = params.rename(columns={'excess_return':'beta_market','SMB':'beta_smb',
                                'HML':'beta_hml','const':'alpha'})
params = params.sort_values(by='alpha',ascending=False)

# Print out stocks with the highest alpha, sort by descending rsquared
print(params.head(50).sort_values(by='rsquared',ascending=False))

