# -*- coding: utf-8 -*-
"""
Created on Wed Aug 18 14:54:59 2021

@author: mateo
"""

import json
import pandas as pd

def cargar_json(x):
    import json
    with open(x+'.json', 'r') as fp:
        x = json.load(fp)
        return  x
 
def quick_to_df(x, trim = False):
    if trim == False:
        df_anual = x['financials']["annual"]
        return pd.DataFrame(df_anual)
    else:
        df_quart = x['financials']["quarterly"]
        return pd.DataFrame(df_quart)