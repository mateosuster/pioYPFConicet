# -*- coding: utf-8 -*-
"""
Created on Thu Jun 17 22:35:02 2021

@author: mateo
"""

# =============================================================================
# librerias
# =============================================================================

import os
os.chdir("C:/Archivos/repos/pioYPFConicet/analisis/quick fs")
os.getcwd()

import requests
from quickfs import QuickFS
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from funciones import *
# import datetime as dt 


# =============================================================================
# # load the key from the enviroment variables
# =============================================================================
api_key = 'c900c59815d8f514ed448346237824a6aff14c7c'
client = QuickFS(api_key)

# Returns your current API usage and limits
client.get_usage()

# =============================================================================
# Metadata (no consumen request)
# =============================================================================

# Request reference data for the supported companies
metadata = client.get_api_metadata()

#empresas actualizadas hasta la fecha yyyymmdd
# client.get_updated_companies(country='US', date='20210601')

#empresas disponibles
## NYSE
companies_nyse = client.get_supported_companies(country='US', exchange='NYSE')
type(companies_nyse )

## OTC
companies_otc = client.get_supported_companies(country='US', exchange='OTC')
type(companies_otc )

"YPF:US" in companies_nyse
"F:US" in companies_otc
"YPF:NYSE" in companies_nyse
"F:US" in companies_nyse
"YPF:OTC" in companies_otc
"SNPKF:USD" in companies_nyse
"SNPKF:OTC" in  companies_otc

[s for s in companies_otc if "SNPKF" in s]
[s for s in companies_nyse if "F:US" in s]

# Available metrics in the API
metrics = client.get_available_metrics()
metrics 

# pd.set_option('display.max_rows', 500)
# pd.set_option('display.max_columns', 500)
# pd.set_option('display.width', 1000)

# =============================================================================
# Descargar all data
# =============================================================================
cwegf = client.get_data_full(symbol="CWEGF:US" )

# json save
with open('cwegf.json', 'w') as fp:
    json.dump(cwegf , fp)

# =============================================================================
# cargo data
# =============================================================================
ypf = cargar_json("ypf")
petrobras = cargar_json("petrobras")
permex = cargar_json("permex")
chevron = cargar_json("chevron")
exxon = cargar_json("exxon")
total = cargar_json("total")
shell = cargar_json("shell")
bp = cargar_json("bp")
sinopec = cargar_json("sinopec")
china_petro = cargar_json("china_petro")
petrochina = cargar_json("petrochina")
marathon = cargar_json("marathon")
suncor = cargar_json("suncor")
equinor = cargar_json("equinor")
conoco= cargar_json("conoco")
phillips66 = cargar_json("phillips66")
valero = cargar_json("valero")
hess = cargar_json("hess")
hollyfrontier = cargar_json("hollyfrontier")
cvr = cargar_json("cvr")
pbf  = cargar_json("pbf")
delek = cargar_json("delek")
trecora = cargar_json("trecora")
bpt = cargar_json("bpt")
cwegf  = cargar_json("cwegf")
lukoy= cargar_json("lukoy")


empresas = { "YPF": ypf, "Petrobras": petrobras, "Permex": permex,
            "BP": bp, "Trecora": trecora, "BPT": bpt, "Crew Energy": cwegf ,
            "LUKoil": lukoy, "CVR": cvr, "PBF": pbf, "Delek": delek,
            "Marathon": marathon, "Valero": valero, "Hess": hess, "HollyFrontier": hollyfrontier,
            "Phillips66": phillips66, "Suncor":suncor, "Equinor":equinor, "Conoco": conoco,
            "Exxon": exxon,"Chevron": chevron , "Shell": shell, "Total": total,
            "China Petroleum": china_petro, "Sinopec": sinopec, "PetroChina": petrochina }

dfs = {}
for key, value in empresas.items():
    dfs["{0}".format(key)] = quick_to_df(value, trim= True)

for key in empresas.keys():
    dfs[key]["company"] = key

df = pd.DataFrame(columns = dfs["YPF"].columns )
for key in empresas.keys():
    df = pd.concat([df , dfs[key]] )

df_new = df.drop(["period_end_date", "company"], axis = 1)
df_new = df_new.apply( lambda x: pd.to_numeric( x , errors='coerce') )
df_new = df_new.apply(np.int64)

df_final = pd.concat([df[["period_end_date", "company"]], df_new ], axis = 1)

df = df_final.copy()

df["period_end_date"] = pd.to_datetime(df["period_end_date"], format = "%Y-%m")
df["date"] = pd.to_datetime(df["period_end_date"], format = "%Y-%m")
df["quarter"] = pd.PeriodIndex(df["date"], freq = "Q")
df.set_index("quarter", inplace = True)

# new variables
df["netdebt_ebitda"] = df["net_debt"]/df["ebitda"]
df["debt_equity"] = (df["lt_debt"]+df["st_debt"])/df["total_equity"]
df["debt_sales"] = (df["total_liabilities"])/df["sga"]

from sklearn.preprocessing import StandardScaler

#escalamiento
std_scaler = StandardScaler()
df["netdebt_ebitda"].replace([np.inf, -np.inf], np.nan, inplace=True)
df["netdebt_ebitda_scale"] = std_scaler.fit_transform(df["netdebt_ebitda"].values.reshape(-1,1) )



df["netdebt_ebitda_scale"] = df["netdebt_ebitda"].apply(lambda x: std_scaler.fit_transform(x))
df["netdebt_ebitda_scale"] = df["netdebt_ebitda"].apply(lambda x: np.mean(x, skipna = True) )
df["netdebt_ebitda_scale"] = df["netdebt_ebitda"].mean(skipna = False) 

np.isinf(np.array(df))

np.isnan(np.array(df)).any()

columns= df.select_dtypes(include=np.number).columns.tolist() 
x= df.select_dtypes(include=np.number)



# total liabilities
sns.lineplot(x = df.period_end_date,
             y = df.total_liabilities,
             hue = df.company).set_title("Total liabilities")
plt.ylabel("USD")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

# Debt to Equity
debt_equity_avg = df.groupby("period_end_date", as_index= False).agg({"debt_equity":"mean"})
sns.lineplot(x = "period_end_date",
             y = "debt_equity",
             hue = "company",
             data =  
              df[df["company"].isin([ "YPF"])]
             # df[df["debt_to_equity"].between( 0, 1)]
              # df[~df["company"].isin([ "CVR"])]
             ).set_title("Debt to Equity")
sns.lineplot(x = "period_end_date",
             y = "debt_equity", data = debt_equity_avg, label = "Simple mean" )
plt.ylabel("")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)


# debt / sales
df["debt_sales"].replace([np.inf, -np.inf], np.nan, inplace=True)
debt_sales_avg = df.groupby("period_end_date", as_index= False).agg({"debt_sales": lambda x: x.mean(skipna= True)})
sns.lineplot(x = "period_end_date",
             y = "debt_sales",
             hue = "company",
             data =  
              df[df["company"].isin([ "YPF"])]
              # df[df["debt_sales"].between( 0, 50)]
              # df[~df["company"].isin([ "CVR"])]
             ).set_title("Total liabilities/Sales")
sns.lineplot(x = "period_end_date", y = "debt_sales", data = debt_sales_avg, label = "Simple mean")
plt.ylabel("")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
plt.axhline(0, color = "black")


# net_debt/ebitda ratio
sns.lineplot(x = "period_end_date",
             y = "netdebt_ebitda",
             hue = "company", data = df[df["company"].isin([
                 "YPF", "Total", 
                  "Chevron", "Exxon", "Marathon"
                 # ,"PetroChina"
                 ]) ]
             )
plt.title("Net Debt/EBITDA")
plt.ylabel("")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

# Cash flow debt issued (cff_debt_issued) 
sns.lineplot(x = "period_end_date",
             y = "cff_debt_issued",
             hue = "company", data =  df[~df["company"].isin(["Sinopec", "PetroChina", "China Petroleum"]) ])
plt.title("Debt Issued")
plt.ylabel("USD")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

# YPF  Cash flow debt issued (cff_debt_issued) 
sns.lineplot(x = "period_end_date",
             y = "cff_debt_net",
             hue = "company", data =  df[df["company"].isin(["YPF", "Petrobras"]) ])
plt.title("Debt Issued")
plt.ylabel("USD")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
plt.axhline(0, color = "b")


# Cash flow debt Repaid (cff_debt_repaid) 
sns.lineplot(x = "period_end_date",
             y = "cff_debt_repaid",
             hue = "company", data =  df[~df["company"].isin(["Sinopec"]) ])
plt.title("Debt Repaid")
plt.ylabel("USD")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)

# Cash flow debt net (cff_debt_net) 
sns.lineplot(x = "period_end_date",
             y = "cff_debt_net",
             hue = "company", data =  df[df["company"].isin(["YPF", "Petrobras"]) ])
plt.title("Cash Flow Debt Net")
plt.ylabel("USD")
plt.xlabel("")
plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
plt.axhline(0, color = "grey")


# funciones para scalar
def scale(x):
    return (x - x.mean(skipna=True))/x.sd()

def z_score(df):
    # copy the dataframe
    df_std = df.copy()
    # apply the z-score method
    for column in df_std.columns:
        df_std[column] = (df_std[column] - df_std[column].mean()) / df_std[column].std()
        
    return df_std
df_scale = z_score(df)





###########
debt = {}
for key, value in dfs.items():
    debt["tot_liab_{}".format(key)] = [key, value["total_liabilities"]]

lista = []
for key, value in dfs.items():
    lista.append(    [key, value["total_liabilities"]])

###
debt = {}
for key, x in dfs.items():
    # print(key)
    debt["tot_liab_{}".format(key)] = [x["period_end_date"], x["total_liabilities"]]
    debt["debt_inc_{}".format(key)] = [x["period_end_date"], x["net_income"]/ x["total_liabilities"] ]


###
ratios = {}
for key, x in dfs.items():
    # print(key)
    ratios["{}".format(key)] = {"period":x["period_end_date"] ,  "total_liab": x["total_liabilities"] ,
                                 "income_liab": x["net_income"]/ x["total_liabilities"] }

for key  in empresas.keys():
    globals()[key]["empresa"] = key



total_liab = {key:val for key, val in debt.items() 
                   if key.startswith("tot_liab")}

total_liab_df = pd.DataFrame(total_liab.values(), columns = empresas.keys())

# =============================================================================
# YPF 
# =============================================================================


ypf["metadata"].keys()
ypf["metadata"]["sic"]
ypf['financials'].keys()

#ypf anual
ypf_annual = quick_to_df(ypf, trim=False)

# ypf trim
ypf_quart = quick_to_df(ypf, trim=True)


# =============================================================================
# Chevron
# =============================================================================
# json save
chevron = cargar_json("chevron")


hertz = client.get_data_full(symbol=  "HTZ:US" ) 

with open('hertz.json', 'w') as fp:
    json.dump(hertz , fp)


# China petroleum,  sinopec y bp


# loop con simbolos
simbolos = {"sinopec": "SNPKF:US", "china_petro": "SNP:US", \
            "bp": "BP:USD", "shell": "SHLX:US", "petrochina": "PCCYF:US" }

shell= client.get_data_full(symbol=  simbolos["shell"] ) 
    
shell

guardar_json(shell)


simbolos = {"sinopec": "SNPKF:US", "china_petro": "SNP:US"}
            
for key, value in simbolos.items():
    print(key, value)    

for key, value in simbolos.items():
    # key = client.get_data_full(symbol= value )


# =============================================================================
# Request con SIC
# =============================================================================

# terminales y autopartes  
# 3711 y 3714  
# mineria, refinacion y extraccion de petroleo, tubos sin costura y aceros plano

# reques de prueba con SINOPEC
header = {'x-qfs-api-key': api_key}

request_body = {
    "data" : {
        "roa" : {
            "SINOPEC" : "QFS(SNPKF:US,roa,FY-2:FY)"},
        "roic" : {
            "SINOPEC" : "QFS(SNPKF:US,roic,FY-2:FY)"
            }
    }
}

r = requests.post("https://public-api.quickfs.net/v1/data/batch",
                  json=request_body,
                  headers=header)

print(r.status_code, r.reason)
my_data = r.json()
print(my_data)

### request prueba sic
request_body = {
    "data" : {
        "roa" : {
            "ford" : "QFS( F:US,roa, FY-9:FY)"}
        }
    }


reque_body  = {
    "data" : {
        "SIC" : {
            "Ford" : "QFS(F:US,sic,FY-2:FY)",
            "PepsiCo" : "QFS(PEP:US,sic,FY-2:FY)"
         },
        "roic" : {
            "Ford" : "QFS(F:US,roic,FY-2:FY)",
            "PepsiCo" : "QFS(PEP:US,roic,FY-2:FY)"
         }
    }
}

reque = requests.post("https://public-api.quickfs.net/v1/data/batch",
                  json=reque_body,
                  headers=header)

print(reque.status_code, reque.reason)

terminales_data = reque.json()
print(terminales_data )


