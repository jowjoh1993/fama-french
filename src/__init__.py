# -*- coding: utf-8 -*-
"""
Created on Sun Jun 27 10:39:23 2021

@author: saknox
"""
from pip._internal import main as pip
#import os
from SchemaUtils import SchemaUtils
package_names = [
    'py-tda-api'
]
pip(['install','--verbose']+package_names)
x = SchemaUtils()
#path = os.path.abspath(x.__file__)

