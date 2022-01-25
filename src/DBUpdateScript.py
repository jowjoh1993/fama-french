# -*- coding: utf-8 -*-
"""
Created on Wed Jun 30 16:57:19 2021

@author: saknox
"""
package_names = [
    'psycopg2',
    'pandas',
    'numpy'
]
import pandas as pd
import requests
import json
import time
import datetime
from td.credentials import TdCredentials
from td.client import TdAmeritradeClient
from td.exceptions import NotFndError, NotNulError
from TDA.config import CONSUMER_KEY, REDIRECT_URI, JSON_PATH
from SchemaUtils import SchemaUtils
schema = SchemaUtils()

class DBUpdateScript:

    def __init__(self):
        self.data = []
    
    def login(self):
        td_credentials = TdCredentials(client_id=CONSUMER_KEY, redirect_uri=REDIRECT_URI,credential_file=JSON_PATH)
        td_client = TdAmeritradeClient(credentials=td_credentials)
        return td_client
    #end def

    # Converts 'milliseconds since epoch' to 'YYYY-MM-DD'
    def epoch_to_datetime(self,epoch_time):
        return time.strftime('%Y-%m-%d', time.localtime(epoch_time/1000))
    #end def

    def get_latest_date(self, df, date):
        epoch_time = datetime.datetime.strptime(date,'%Y-%m-%d').timestamp()*1000
        return int(epoch_time)

    # Subsets the historical price data returned from API calls
    def slice_price_data(self,symbol,data):
        data = data['candles']
        df = pd.DataFrame(data)[['close','datetime']]
        df['datetime'] = df['datetime'].apply(self.epoch_to_datetime)
        df = df.rename(columns={'close':symbol,'datetime':'date'})
        df = df.set_index('date')
        return df
    #end def

    # Make GET requests to the TD Ameritrade API for fundamental data
    # Inputs
    #    symbol : symbol of the stock whose data you want, e.g. "GOOG"
    #    access_token: OAuth2 access token for API authentication
    # Outputs
    #    JSON object containing fundamental data for the stock
    def get_fundamentals(self,symbol,td_client):
        
        print("Getting fundamental data for "+symbol+"...")
        try:
            instruments = td_client.instruments()
            response = instruments.search_instruments(symbol=symbol,projection='fundamental')
        except requests.exceptions.ConnectionError:
            print("WARNING: Connection failure")
            response = {"keys":""}

        return response
    #end def
    
    # Make GET requests to the TD Ameritrade API for price history data
    # Feel free to change the default argument values if you prefer different
    # periods or frequencies for your data, or just call the function with
    # different arguments.
    # IMPORTANT: If you change the frequency to something other than "daily", you
    # must also change the calculation of the risk free return in the "Calculate
    # returns" section below to match.
    def get_prices(self,
                   symbol,
                   td_client,                
                   periodType = "year",
                   period = 1,
                   frequencyType = "daily",
                   frequency = 1,
                   end_date = None
                   ):
    
        print("Getting price data for "+symbol+"...")
        try:
            prices = td_client.price_history()
            response=prices.get_price_history(symbol=symbol,
                                         period_type=periodType,
                                         period=period,
                                         frequency_type=frequencyType,
                                         frequency=frequency,
                                         end_date=end_date
                                        )
            print(response)
        except NotFndError:
            print("Price data not found... continue")
            return
        except requests.exceptions.ConnectionError:
            print("WARNING: Connection failure")
            return
        except NotNulError:
            print("None found")
        return response
    #end def    
    
    def getFundamentalsData(self,sector_list,tickers,td_client):
        keys_to_keep=["symbol","marketCap","bookValuePerShare","sharesOutstanding"]        
        
        # Initialize the data frame to hold fundamental data
        fundamentals = pd.DataFrame()

        for sector in sector_list:
            symbol_list=tickers[tickers['Sector'] == sector]['Symbol'].tolist()
            for sym in symbol_list:
                # Call get_fundamentals and convert JSON to dictionary
                temp = self.get_fundamentals(sym, td_client)
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
        #end for

        # Calculate book-to-market ratio
        fundamentals['equity'] = fundamentals['bookValuePerShare'] * \
                                    fundamentals['sharesOutstanding']
        fundamentals['bookToMarket']=fundamentals['equity'] / fundamentals['marketCap']
        
        return fundamentals                
    
    def updateFundamentalsTable(self,fundamentals):    
        fundamentals_columns = fundamentals.columns.tolist()
        index = fundamentals_columns.pop(0)
        fundamentals=fundamentals.set_index(index)
        schema.executeCreateTableStatement(columns=fundamentals_columns,table_name='fundamentals',index=index)
        schema.executeInsertStatement(df=fundamentals,table_name='fundamentals',index=index)

    def updatePricesTables(self,sector_list,tickers,td_client):
        # Maximum number of NaNs allowed in price history
        nan_limit = 10

        # Get the historical stock prices for symbols in symbol_list
        firstPrices = True
        for sector in sector_list:
            firstPrice = True
            symbol_list=tickers[tickers['Sector'] == sector]['Symbol'].tolist()
            for sym in symbol_list:
                result = self.get_prices(symbol=sym,td_client=td_client)
                if result is not None:
                    if not result['empty']:
                        df = self.slice_price_data(sym,result)
                        if firstPrice:
                            price = df
                            firstPrice = False
                        else:
                            price = pd.merge(price, df, how='outer',left_index=True,
                                         right_index=True)
                    else:
                        print("WARNING: dataframe is empty")
                    #end if
                else:
                    print("WARNING: " + sym + " is an invalid stock ticker symbol!")
                #end if
                time.sleep(0.3) # As before, can't make too many API requests per second
            #end for
    
            # Drop any column with too much missing data
            for col in price.columns:
                if price[col].isna().sum() > nan_limit:
                    print("WARNING: NaN limit exceeded! Dropping " + col + ".")
                    price = price.drop(columns=[col])
                #end if
            #end for    
    
            price_columns=schema.removeKeywordsFromSymbols(price.columns.tolist())
            price.columns = price_columns
            schema.executeCreateTableStatement(columns=price_columns,table_name=sector,index='Date')
            schema.executeInsertStatement(df=price,table_name=sector,index='Date')
    
            if firstPrices:
                prices = price
                firstPrices = False
            else:
                prices = pd.merge(prices, price, how='outer',left_index=True,
                                  right_index=True)        
            #end if
        #end for        
    #end def
        
    def main(self):
        print("Hello World!")

    if __name__ == "__main__":
        from DBUpdateScript import DBUpdateScript
        update = DBUpdateScript()
        td_client = update.login()        
        tickers = schema.getTickers()
        sector_list = schema.getSectorList()

        fundamentals = update.getFundamentalsData(sector_list,tickers,td_client)
        update.updateFundamentalsTable(fundamentals)
        update.updatePricesTables(sector_list,tickers,td_client)
        
        