# -*- coding: utf-8 -*-
"""
Created on Fri Nov  5 07:55:37 2021

@author: saknox
"""

import pandas as pd
from datetime import datetime
from DBUpdateScript import DBUpdateScript
    
def test_epoch():
    df = pd.DataFrame(data = {'date': ['2021-10-18','2021-10-19'], 'aaon': [71.46, 72.10], 'aca': [18.67, 18.56]}).set_index('date')
    print(df.index)
    max_date = datetime.strptime("1967-01-01","%Y-%m-%d")
    for i, rows in df.iterrows():
        current_date = datetime.strptime(i, "%Y-%m-%d")
        if(current_date > max_date): 
            max_date = current_date
    print(max_date)
    assert 
    update = DBUpdateScript()        
    epoch_time = update.get_latest_date(df, '2021-10-19')
    print(epoch_time)
    assert epoch_time == 1634616000000
    
test_epoch()