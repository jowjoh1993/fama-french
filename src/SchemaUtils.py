# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

import psycopg2, pandas as pd, numpy as np, os
from psycopg2 import extras
from psycopg2.extensions import register_adapter, AsIs
import pandas.io.sql as sqlio

class SchemaUtils:
    
    def __init__(self):
        self.data = []
    
    def writeCreateTableStatement(self,columns,table_name,index):
        create_statement = 'DROP TABLE IF EXISTS price_data.'+table_name+';CREATE TABLE IF NOT EXISTS price_data.'+table_name+' ( '+index+' VARCHAR(255)'
        print(create_statement)
        for column in columns:
            create_statement+=str(', '+column+' double precision')
        create_statement+=');'
        return create_statement

    def executeCreateTableStatement(self,columns,table_name,index):
        conn = psycopg2.connect(dbname='postgres', user='postgres', password='g6a!pSMMPOST')
        cursor = conn.cursor()
        create_statement = self.writeCreateTableStatement(columns,table_name,index)
        print(create_statement)
        cursor.execute(create_statement)
        conn.commit()
        cursor.close()
        conn.close()

    def writeInsertStatement(self,df,table_name,index):
        cols = index+','+','.join(list(df.columns))
        insert_statement = "INSERT INTO %s(%s) VALUES %%s" % ('price_data.'+table_name,cols)
        return insert_statement
    
    def executeInsertStatement(self,df,table_name,index):
        register_adapter(np.int64, AsIs)
        conn = psycopg2.connect(dbname='postgres', user='postgres', password='g6a!pSMMPOST')
        cursor = conn.cursor()
        df_values = df.values.tolist()
        for i in range(len(df_values)):
            df_values[i].insert(0,df.index.values[i])
        insert_statement = self.writeInsertStatement(df,table_name,index)
        extras.execute_values(cursor,insert_statement,df_values)
        conn.commit()
        cursor.close()
        conn.close()
    
    def executeSelectStatement(self,table_name,index):
        conn = psycopg2.connect(dbname='postgres', user='postgres', password='g6a!pSMMPOST')        
        select_statement = 'SELECT * FROM price_data.'+table_name
        df = sqlio.read_sql_query(select_statement, conn)
        if index is not None:
            df.set_index(index,drop=True,inplace=True)
        conn.close()
        return df
    
    def removeKeywordsFromSymbols(self,symbols):
        keywords = ['ALL', 'ASC', 'ELSE', 'FOR', 'ON']
        for keyword in keywords:
            try: 
                index=symbols.index(keyword)
                symbols.pop(index)
                symbols.insert(index,'_'+keyword+'_')
            except ValueError:
                print('Keyword '+keyword+' was not found.. moving on.')
        return symbols
    
    def getTickers(self):
        root_dir = os.path.abspath("")
        tickers=pd.read_csv(root_dir+'/../data/asset_universe.csv')
        tickers['Sector']=tickers['Sector'].str.replace('[ -]','_')
        return tickers
    def getSectorList(self):
        tickers = self.getTickers()
        sector_list = tickers.Sector.unique().tolist()
        sector_list.pop(sector_list.index(np.nan))
        return sector_list
    def getConnection(dbname,user,password):
        conn = psycopg2.connect(dbname='postgres', user='postgres', password='g6a!pSMMPOST')
        return conn
    def getCursor(conn):
        cur = conn.cursor()
        return cur    
    def main(self):
        print("Hello World!")

    if __name__ == "__main__":
        from SchemaUtils import SchemaUtils
        schema = SchemaUtils()
        #schema.main()
        conn = psycopg2.connect(dbname='postgres', user='postgres', password='g6a!pSMMPOST')
        tickers = getTickers(schema)
        sector_list = tickers.Sector.unique().tolist()
        sector_list.pop(sector_list.index(np.nan))
        cur = getCursor(conn)
        for sector in sector_list:
            symbols=tickers[tickers['Sector'] == sector]['Symbol'].tolist()
            symbols=schema.removeKeywordsFromSymbols(symbols)
            command=schema.writeCreateTableStatement(symbols,sector,'Date')
        df=schema.executeSelectStatement('fundamentals',None)
        cur.execute(command)
        conn.commit()
        cur.close()
        conn.close()
    