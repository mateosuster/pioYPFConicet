import os, requests
import time                                                                                                                  
import os
from dotenv import load_dotenv
from pathlib import Path                                                                                                             

load_dotenv(Path("src/comtrade_download.py").resolve().parent.parent / ".env")                                                        
API_KEY = os.environ["COMTRADE_API_KEY"]    

# tests = [      ("S1", "331",  "crude Rev1"),
#     ("S2", "333",  "crude Rev2"),
#     ("S3", "333",  "crude Rev3"),
#       ("S3", "3411", "gas liq S3"),
#       ("S3", "3412", "gas pipe S3"),      ("S3", "341",  "gas group S3"),
#       ("S4", "333",  "crude S4"),      ("S4", "3411", "gas liq S4"),      ("S4", "3412", "gas pipe S4"),
# ]
# for cl, code, label in tests:      
#     url = f"https://comtradeapi.un.org/data/v1/get/C/A/{cl}"
#     r = requests.get(url, params={
#         "reporterCode": "32", "partnerCode": "0",       
#         "cmdCode": code, "flowCode": "X",
#         "period": "2000,2001,2002",
#         "subscription-key": API_KEY,     
#         },
#           timeout=60)
#     data = r.json()
#     n = len(data.get("data", []))
#     print(f"{cl} {code:6s} ({label}): {n} rows | {data.get('message','')[:60]}")     
#     time.sleep(3)

# tests = [
#       ("S3", "341",  "1970,1975,1980"),      ("S3", "3411", "1970,1975,1980"),      ("S3", "3412", "1970,1975,1980"),
#       ("S3", "341",  "1985,1990,1995"),      ("S3", "3412", "1985,1990,1995"),
#       ("S2", "3412", "1985,1990,1995"),
#       ("S2", "341",  "1985,1990,1995"),  ]

# for cl, code, period in tests:    
#     url = f"https://comtradeapi.un.org/data/v1/get/C/A/{cl}"
#     r = requests.get(url, params={
#         "reporterCode": "32", "partnerCode": "0",          "cmdCode": code, "flowCode": "X",
#         "period": period,          "subscription-key": API_KEY,
#     }, timeout=60)
#     data = r.json()
#     n = len(data.get("data", []))
#     print(f"{cl} {code:6s} {period}: {n} rows")
#     time.sleep(3)

# ● S2 341 (3-digit group) has gas data. Now check crude coverage with S2, and gas with S3 for recent years:

tests = [
      ("S2", "333",  "1985,1990,1995", "crude S2 historical"),
      ("S2", "333",  "2000,2005,2010", "crude S2 recent"),      ("S3", "333",  "1985,1990,1995", "crude S3 historical"),
      ("S2", "341",  "2000,2005,2010", "gas S2 recent"),
      ("S3", "341",  "2000,2005,2010", "gas S3 recent"),      ("S2", "341",  "1970,1975,1980", "gas S2 early"),
  ]
for cl, code, period, label in tests:
      url = f"https://comtradeapi.un.org/data/v1/get/C/A/{cl}"
      r = requests.get(url, params={
          "reporterCode": "32", "partnerCode": "0",
          "cmdCode": code, "flowCode": "X",          "period": period,
          "subscription-key": API_KEY,      }, timeout=60)
      data = r.json()
      n = len(data.get("data", []))
      print(f"{cl} {code} {period} ({label}): {n} rows")    
      time.sleep(3)