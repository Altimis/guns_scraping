# Import data
import pandas as pd
import numpy as np
import requests

import subprocess
import sys
from time import sleep
from datetime import datetime
import json
import config

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(message)s')


##########
# config #
##########

csv_path = config.csv_path
columns = config.columns
device_name = config.device_name
user_agent = config.user_agent
api_label_1 = config.api_label_1
api_label_2 = config.api_label_2
token = config.token
url = config.url
username = config.username
password = config.password

## create a class to use to initiate object
class api_wrapprer:
    """
    Class that wraps fata from the API
    """
    #initiator to create objects
    def __init__(self,csv_file='sample.csv',logs ='logs.txt'):
        self.csv_file = csv_file
        self.logs = logs

    # write logs into a txt file
    def write_log(self,txt):
        with open(self.logs, 'a') as fl:
            fl.write(txt + '\n')

    # get the minimal price from distributor_items prices
    def get_price_from_distributor_items(self, lst):
        prices = []
        for elt in lst:
            price = elt['price']
            if price:
                prices.append(float(price.replace('$', '').replace(',', '')))
        if prices:
            distributor_items_price = np.min(prices)
            return distributor_items_price
        else:
            print("No distributed price found")
            return

    # pad the upc with 0s
    def pad_upc(self, upc):
        upc = str(upc)
        if len(upc) == 12:
            return "'" + upc + "'"
        elif len(upc) < 12:
            pad_n = 12-len(upc)
            upc = '0'*pad_n + upc
            return "'" + upc + "'"
        else:
            print("upc has len : ", len(upc))
            return "'" + upc + "'"

    # main function that sends data to the cloud via API
    def get_items(self):
        logging.info("Starting get_items")
        to_return = []
        try:
            self.write_log(f'Trying to push data via API')
            i = 1
            total = 1
            while i <= total:
                params = {
                    "page": i
                }
                print("current page : ", i)
                # get the response
                response = requests.get(url, auth=(username, password), params=params)
                # retrieve data from the response json
                if int(response.status_code) == 200:
                    logging.info("Success response")
                    for elt in response.json()['results']:
                        row = {}
                        # upc
                        upc = self.pad_upc(elt['upc'])
                        if upc:
                            print("UPC : ", upc)
                            row['upc'] = upc
                        else:
                            row['upc'] = None
                        # price
                        price = float(elt['price'].replace('$', '').replace(',', ''))
                        if price:
                            print("Price : ", price)
                            row['price'] = price
                        else:
                            row['price'] = None
                        # distributor price
                        distributor_items_price = self.get_price_from_distributor_items(elt['distributor_items'])
                        row['distributor_items_price'] = distributor_items_price
                        print("distributor_items_price : ", distributor_items_price)
                        # category name
                        category_name = elt['category_name']
                        row['category_name'] = category_name
                        print("category name : ", category_name)
                        to_return.append(row)
                        print("---")
                    total = int(response.json()['pages'])
                    print("pages left : ", total-i)
                    i += 1
                    print("items pulled : ", len(to_return))
                    df = pd.DataFrame.from_dict(to_return)
                    df.to_csv("data/results_csv.csv", index=False)
               
                    with open("data/results_json.json", "w") as final:
                        json.dump(to_return, final, indent= 4)
                else:
                    print(f'Error getting data'+str(response.json()))
                    self.write_log(f'Error getting data'+str(response.json()))

        except Exception as e:
            print(e)
            self.write_log(f'Error in API process => {str(e)}')


if __name__ == "__main__":
        print("welcome  ")
        tst = api_wrapprer(csv_file=csv_path)
        tst.get_items()
        print("Code finished running")
        sleep(10)