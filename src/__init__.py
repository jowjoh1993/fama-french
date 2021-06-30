# -*- coding: utf-8 -*-
"""
Created on Sun Jun 27 10:39:23 2021

@author: saknox
"""
import pip
import os
from SchemaUtils import SchemaUtils
package_names = [
    'psycopg2',
    'pandas',
    'numpy',
    'td-ameritrade-python-api'
]
pip.main(['install']+package_names)
x = SchemaUtils()
path = os.path.abspath(x.__file__)

