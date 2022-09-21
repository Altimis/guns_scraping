import logging
import boto3
from botocore.exceptions import ClientError
from flask import Flask
import re
import pandas as pd
import os
import numpy as np
import math
from waitress import serve
import chromedriver_autoinstaller
import config
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import random
import logging
import traceback
import selenium
from time import sleep

import itertools
from threading import Thread

import csv
import json

import requests

from datetime import datetime as dt

import warnings

import os
import stat

##########
# config #
##########

user_agent = config.user_agent
token = config.token
api_url = config.url
username = config.username
password = config.password

# call s3 bucket
s3 = boto3.resource('s3', aws_access_key_id=config.ACCESS_ID, aws_secret_access_key=config.ACCESS_KEY)
bucket = s3.Bucket(config.BUCKET_NAME)


class Scraper:
    def __init__(self, barcodelookup_url, gunengine_url, gundeals_url, wikiarms_url):
        self.upcs_products = []
        print("Setting up the main class")
        self.barcodelookup_url = barcodelookup_url
        self.gunengine_url = gunengine_url
        self.gundeals_url = gundeals_url
        self.wikiarms_url = wikiarms_url
        # print("self.gundeals url : ", self.gundeals_url)
        self.failed = False

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
            pad_n = 12 - len(upc)
            upc = '0' * pad_n + upc
            return "'" + upc + "'"
        else:
            # print("upc has len : ", len(upc))
            return "'" + upc + "'"

    def log_to_file(self, string):
        print(string)
        with open("tmp/logs.txt", "a") as f:
            f.write(string + '/n')

    # main function that sends data to the cloud via API
    def get_items(self):
        s3 = boto3.client('s3', aws_access_key_id=config.ACCESS_ID, aws_secret_access_key=config.ACCESS_KEY)

        # read the file

        s3.download_file(config.BUCKET_NAME, 'layers/timestamps.txt', 'tmp/timestamps.txt')

        os.chmod('tmp/timestamps.txt', 0o777)

        with open('tmp/timestamps.txt', 'r') as f:
            lines = f.readline()
            lines = lines.split('/n')
            lines = [line.rstrip() for line in lines if line]

        if lines:
            timestamps = [dt.strptime(line, '%Y-%m-%d_%H-%M-%S') for line in lines]
            latest_timestamp = max(timestamps)
            print("latest df : ", latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S'))
            s3.download_file(config.BUCKET_NAME, f"data/results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv",
                             f"tmp/results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv")
            latest_df = pd.read_csv(f"tmp/results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv")
            target_prices = latest_df.target_price.values.tolist()
            # print("target price : ", target_prices)
            price_difference_percents = latest_df.price_difference_percent.values.tolist()
            price_difference_amounts = latest_df.price_difference_amount.values.tolist()
            is_completed = all(
                (not math.isnan(el1) or not math.isnan(el2) or not math.isnan(el3)) for el1, el2, el3 in zip(
                    target_prices, price_difference_percents, price_difference_amounts))
            nothing = False
        else:
            nothing = True
            is_completed = True

        if is_completed:
            if nothing:
                self.log_to_file("This is the first scraping session. First csv will be created.")
            else:
                warning_upcs = latest_df[np.abs(latest_df['price_difference_percent']) > config.threshold][
                    'upc'].values.tolist()
                self.log_to_file(f"Warning for these UPCs : {warning_upcs}")
                print("Completed.")
                self.log_to_file("All csvs are completed. Creating a new scraping session.")
            now = dt.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.ucp_csv_path = f"tmp/results_{now}.csv"
        else:
            self.ucp_csv_path = f"tmp/results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            self.log_to_file(f"The file results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv "
                             f"is not completed. Resuming scraping.")
            return

        to_return = []
        try:
            i = 1
            total = 1
            while i <= 1:  # total:
                params = {
                    "page": i
                }
                # print("current page : ", i)
                # get the response
                response = requests.get(api_url, auth=(username, password), params=params)
                # retrieve data from the response json
                if int(response.status_code) == 200:
                    for elt in response.json()['results']:
                        row = {}
                        # upc
                        upc = self.pad_upc(elt['upc'])
                        if upc:
                            # print("UPC : ", upc)
                            # if upc != "'723189045227'":
                            #    continue
                            row['upc'] = upc
                        else:
                            row['upc'] = None
                        # price
                        price = float(elt['price'].replace('$', '').replace(',', ''))
                        if price:
                            # print("Price : ", price)
                            row['price'] = price
                        else:
                            row['price'] = None
                        # distributor price
                        distributor_items_price = self.get_price_from_distributor_items(elt['distributor_items'])
                        row['distributor_items_price'] = distributor_items_price
                        # print("distributor_items_price : ", distributor_items_price)
                        # category name
                        category_name = elt['category_name']
                        row['category_name'] = category_name
                        product_type = elt['product_type']
                        row['product_type'] = product_type
                        # print("category name : ", category_name)
                        to_return.append(row)
                    total = int(response.json()['pages'])
                    # print("pages left : ", total - i)
                    i += 1
                    # print("items pulled : ", len(to_return))

                    df = pd.DataFrame.from_dict(to_return)

                    df['target_price'] = ''
                    df['price_difference_percent'] = ''
                    df['price_difference_amount'] = ''

                    df = df.sample(frac=0.13)

                    # print(self.ucp_csv_path)

                    df.to_csv(self.ucp_csv_path, index=False)

                    with open(self.ucp_csv_path, 'r') as infile:
                        reader = list(csv.reader(infile))
                        reader = reader[::-1]  # the date is ascending order in file
                        # reader.insert(0,lists)

                    with open(self.ucp_csv_path, 'w', newline='') as outfile:
                        writer = csv.writer(outfile)
                        for line in reversed(reader):  # reverse order
                            writer.writerow(line)
                    # upload file from tmp to s3 key
                    bucket.upload_file(self.ucp_csv_path, 'data/' + self.ucp_csv_path.split('/')[-1])

                else:
                    self.log_to_file(f'Error getting data' + str(response.json()))

            # write the time to file
            with open('tmp/timestamps.txt', 'a') as f:
                f.write(now)
                f.write('/n')

            bucket.upload_file('tmp/timestamps.txt', 'layers/timestamps.txt')

        except Exception as e:
            print(e)

        return len(df)

    def scrape_wikiarms(self, ucp, product_type):
        """
        scrape barcodelookup websites
        """
        # iterate through all ucps
        # for ucp in self.ucps:
        scraper_name = 'wikiarms'
        cat_names = {
            'guns': ['Handgun', 'Long Gun'],
            'ammo': ['Ammunition'],
            'parts': ['Suppressor', 'Merchandise']
        }
        ucp = ucp.replace("'", "")
        stores_prices = []
        f = False
        for key, value in cat_names.items():
            if product_type in value:
                cat_name = key
                f = True
                break
        if not f:
            cat_name = 'guns'
        # intiate the driver
        driver = self.init_driver()
        if not driver:
            self.log_to_file(f"[{scraper_name}] there was a fatal problem with the chromedriver intialization!")
            self.failed = True
            return
        # get the url
        url = self.wikiarms_url + cat_name + '?q=' + str(ucp)
        self.log_to_file(f"[{scraper_name}] Getting products with UCP : {ucp} : {url}")
        try:
            driver.get(url)
        except:
            err = traceback.format_exc()
            self.log_to_file(f"[{scraper_name}] There was an issue getting the url : {url}"
                             f"\nError Traceback: {err}")
            driver.close()
            return
        # sleep(random.uniform(, 6))

        # self.log_to_file(f"page source : {driver.page_source}")

        # get products elements
        try:
            els = driver.find_elements(By.XPATH, "//div[@id='products-table']/table/tbody/tr")
        except Exception as e:
            err = traceback.format_exc()
            self.log_to_file(f"[{scraper_name}] There was an issue pulling [all products] with the ucp {ucp}"
                             f"\nError Traceback: {e}")
            driver.close()
            return
        self.log_to_file(f"[{scraper_name}] got {len(els)} elements")
        # iterate through all shops
        stores_prices = []
        for el in els:
            # get the price and store elements
            try:
                store_href = el.find_element(By.XPATH, "./td[1]/a").get_attribute('href')
                price = el.find_element(By.XPATH, './td[2]').text
                if price != "MAP":
                    price = float(price.replace('$', '').replace(',', ''))
                else:
                    continue

            except Exception as e:
                err = traceback.format_exc()
                self.log_to_file(f"[{scraper_name}] There was an issue pulling [a product] with the ucp {ucp}"
                                 f"\nError Traceback: {e}")
                continue
            driver2 = self.init_driver()
            if not driver2:
                self.log_to_file(f"[{scraper_name}] there was a fatal problem with the chromedriver intialization!")
                store_url = store_href
            else:
                try:
                    driver2.get(store_href)
                    store_url = store_href
                    i = 0
                    while store_url == store_href and i < 5:
                        sleep(0.5)
                        store_url = driver2.current_url
                        i += 1
                    driver2.close()
                except Exception as e:
                    err = traceback.format_exc()
                    self.log_to_file(f"[{scraper_name}] There was an issue getting the store href : {store_href}"
                                     f"\nError Traceback: {e}")
                    driver2.close()
                    store_url = store_href
                    pass

            # self.log_to_file(f"price : {price}, store_url : {store_url}")

            stores_prices.append((store_url, price))

        # close the driver
        driver.close()
        self.log_to_file(f"[{scraper_name}] got the prices : {stores_prices}")
        # save products for this ucp
        self.upcs_products += stores_prices
        self.log_to_file(f"[{scraper_name}] Finished scraping with {len(stores_prices)} items.")

    def scrape_gunengine(self, ucp, product_type):
        scraper_name = 'gunengine'
        cat_names = {
            'guns': ['Handgun', 'Long Gun'],
            'ammo': ['Ammunition'],
            'parts': ['Suppressor', 'Merchandise']
        }
        ucp = ucp.replace("'", "")
        stores_prices = []
        f = False
        for key, value in cat_names.items():
            if product_type in value:
                cat_name = key
                f = True
                break
        if not f:
            cat_name = 'guns'
        driver = self.init_driver()
        if not driver:
            self.log_to_file(f"[{scraper_name}] there was a fatal problem with the chromedriver intialization!")
            self.failed = True
            return
        # get the url
        url = self.gunengine_url + cat_name + '?q=' + str(ucp)
        self.log_to_file(f"[{scraper_name}] Getting products with UCP : {ucp} : {url} for category {cat_name}")
        try:
            driver.get(url)
        except:
            err = traceback.format_exc()
            self.log_to_file(f"[{scraper_name}] There was an issue getting the url : {url}"
                             f"\nError Traceback: {err}")
            driver.close()
            return
        sleep(random.uniform(0.5, 1))

        # get products elements
        try:
            found = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/p').text
        except:
            sleep(random.uniform(1, 2))
            found = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/p').text

        # continue if 0 products found
        if found:
            if int(re.search(r'\d+', found).group()) == 0:
                self.log_to_file(f"[{scraper_name}] 0 results found for ucp : {ucp}")
                driver.close()
                return
        else:
            self.log_to_file(f"[{scraper_name}] 0 results found for ucp : {ucp}")
            driver.close()
            return

        # show all stores
        try:
            driver.find_element(By.XPATH, f'//*[@id="upc{ucp}"]/a').click()
        except Exception as e:
            self.log_to_file(f"[{scraper_name}] Couldn't get all results for UPC {ucp}")

        sleep(random.uniform(0.5, 1))
        # get stores elements
        try:
            variant_els = driver.find_elements(By.XPATH, "//div[@class='variant']")
        except Exception as e:
            err = traceback.format_exc()
            self.log_to_file(f"[{scraper_name}] There was an issue pulling [all products] with the ucp {ucp}"
                             f"\nError Traceback: {e}")
            driver.close()
            return
        # iterate through all shops
        stores_prices = []
        for variant_el in variant_els:
            # get the price and store elements
            try:
                price = float(variant_el.find_element(
                    By.XPATH, "./div[1]/a[1]/span[@class='variant-price ']").text.replace('$', '').replace(',', ''))
                store_href = variant_el.find_element(
                    By.XPATH, "./div[1]/a[1]").get_attribute('href')
            except Exception as e:
                err = traceback.format_exc()
                self.log_to_file(f"[{scraper_name}] There was an issue pulling [a product] with the ucp {ucp}"
                                 f"\nError Traceback: {e}")
                continue

            driver2 = self.init_driver()
            if not driver2:
                self.log_to_file(f"[{scraper_name}] there was a fatal problem with the chromedriver intialization!")
                store_url = store_href
            else:
                try:
                    driver2.get(store_href)
                    store_url = store_href
                    i = 0
                    while store_url == store_href and i < 5:
                        sleep(0.5)
                        store_url = driver2.current_url
                        i += 1
                    driver2.close()
                except:
                    err = traceback.format_exc()
                    self.log_to_file(f"[{scraper_name}] There was an issue getting the store href : {store_href}"
                                     f"\nError Traceback: {err}")
                    driver2.close()
                    store_url = store_href
                    pass
            # self.log_to_file(f"price : {price}, store_url : {store_url}")
            stores_prices.append((store_url, price))

        # close the driver
        driver.close()
        self.log_to_file(f"[{scraper_name}] got the prices : {stores_prices}")
        # save productsUnnamed: 0 for this ucp
        self.upcs_products += stores_prices
        self.log_to_file(f"[{scraper_name}] Finished scraping with {len(stores_prices)} items.")

    def scrape_gundeals(self, ucp):
        """
        scrape barcodelookup websites
        """
        # iterate through all ucps
        scraper_name = 'gundeals'
        ucp = ucp.replace("'", "")
        stores_prices = []
        # intiate the driver
        driver = self.init_driver()
        if not driver:
            self.log_to_file(f"[{scraper_name}] there was a fatal problem with the chromedriver intialization!")
            self.failed = True
            return
        # get the url
        url = self.gundeals_url + str(ucp)
        self.log_to_file(f"[{scraper_name}] Getting products with UCP : {ucp} : {url}")
        try:
            driver.get(url)
        except:
            err = traceback.format_exc()
            self.log_to_file(f"There was an issue getting the url : {url}"
                             f"\nError Traceback: {err}")
            driver.close()
            return
        sleep(random.uniform(1, 2))

        # get products elements
        try:
            els = driver.find_elements(By.XPATH, "//table[@id='price-compare-table']/tbody/tr")
        except Exception as e:
            err = traceback.format_exc()
            self.log_to_file(f"There was an issue pulling [all products] with the ucp {ucp} from [gundeals] website."
                             f"\nError Traceback: {e}")
            driver.close()
            return

        # iterate through all shops
        stores_prices = []
        for el in els:
            # get the price and store elements
            if 'out of stock' in el.text.lower():
                self.log_to_file(f"[{scraper_name}] out of stock found")
                break
            try:
                price = el.get_attribute('data-price')
                price = float(price.replace('$', '').replace(',', ''))
                store_href = el.find_element(By.XPATH, './/td[1]/div[1]/a[1]').get_attribute('href')
            except Exception as e:
                err = traceback.format_exc()
                self.log_to_file(f"There was an issue pulling [a product] with the ucp {ucp} from [gundeals] website."
                                 f"\nError Traceback: {e}")
                continue

            driver2 = self.init_driver()
            if not driver2:
                self.log_to_file(f"[{scraper_name}] there was a fatal problem with the chromedriver intialization!")
                store_url = store_href
            else:
                try:
                    driver2.get(store_href)
                    store_url = store_href
                    i = 0
                    while store_url == store_href and i < 5:
                        sleep(0.5)
                        store_url = driver2.current_url
                        i += 1
                    driver2.close()
                except:
                    err = traceback.format_exc()
                    self.log_to_file(f"[{scraper_name}] There was an issue getting the store href : {store_href}"
                                     f"\nError Traceback: {err}")
                    store_url = store_href
                    pass

            # self.log_to_file(f"price : {price}, store_url : {store_url}")

            stores_prices.append((store_url, price))

        # close the driver
        driver.close()
        # break
        self.log_to_file(f"[{scraper_name}] got the prices : {stores_prices}")
        # save products for this ucp
        self.upcs_products += stores_prices
        self.log_to_file(f"[{scraper_name}] Finished scraping with {len(stores_prices)} items.")

    def init_driver(self, is_proxy=False):
        """
        initiate the undetected chrome driver
        """
        # intitate the driver instance with options and chrome version
        import os
        #print(os.system('whereis google-chrome'))
        options = uc.ChromeOptions()
        #options.binary_location = 'tmp/headless-chromium'
        #options.add_argument('--no-first-run --no-service-autorun')
        options.add_argument('--headless')
        try:  # will patch to newest Chrome driver version
            print("getting driver")
            driver = uc.Chrome(options=options)
        except Exception as e:  # newest driver version not matching Chrome version
            err = traceback.format_exc()
            print("couldn't get driver : ", err)
        #worked = False
        #attempt = 1
        #while not worked and attempt < 4:
            # self.log_to_file(f"initiating the driver attempt {attempt} ...")

            """
            try:
                chromedriver_path = chromedriver_autoinstaller.install()
                options = uc.ChromeOptions()
                #options.binary_location = 'tmp/headless-chromium'
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--single-process')
                options.add_argument('--disable-dev-shm-usage')
                # set proxy
                if config.is_proxy:
                    proxy = random.choice(config.proxies)
                    options.add_argument(f'--proxy={proxy}')
                driver = uc.Chrome(driver_executable_path='tmp/chromedriver',
                                   options=options)  # , version_main=chrome_version)
                worked = True
                return driver
            except Exception as e:
                self.log_to_file("Exception getting the driver : " + str(e))
                options = uc.ChromeOptions()
                options.binary_location = 'tmp/headless-chromium'
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--single-process')
                options.add_argument('--disable-dev-shm-usage')
                # set proxy
                if config.is_proxy:
                    proxy = random.choice(config.proxies)
                    options.add_argument(f'--proxy={proxy}')
                driver = uc.Chrome(driver_executable_path='tmp/chromedriver', options=options)
                worked = False
            attempt += 1
            """
        return driver

    def load_ucps(self, ucp_csv_path):
        """
        yield each value of upcs and prices from saved API data (generator)
        """
        s3 = boto3.client('s3', aws_access_key_id=config.ACCESS_ID, aws_secret_access_key=config.ACCESS_KEY)
        s3.download_file(config.BUCKET_NAME, 'data/' + ucp_csv_path.split('/')[-1], ucp_csv_path)
        df = pd.read_csv(ucp_csv_path)
        upcs = df.upc.values.tolist()
        prices = df.price.values.tolist()
        target_prices = df.target_price.values.tolist()
        price_difference_percents = df.price_difference_percent.values.tolist()
        price_difference_amounts = df.price_difference_amount.values.tolist()
        product_types = df.product_type.values.tolist()

        for upc, price, target_price, price_difference_percent, price_difference_amount, product_type in zip(
                upcs, prices, target_prices, price_difference_percents, price_difference_amounts, product_types):
            if (math.isnan(target_price) or
                    math.isnan(price_difference_percent) or
                    math.isnan(price_difference_amount)):
                yield upc, price, product_type

    def scrape_all(self):
        """

        """
        # yielding upcs
        self.log_to_file("getting upcs and prices from the API ...")
        len_items = self.get_items()
        if len_items:
            self.log_to_file(f"Got {len_items}")
        else:
            self.log_to_file("an uncompleted csv file already exists")

        upcs_prices_generator = self.load_ucps(self.ucp_csv_path)

        json_upcs_products = {}

        for upc, price, product_type in upcs_prices_generator:
            self.log_to_file(f"scraping for upc {upc} and price {price} ...")
            self.upcs_products = []
            # Scraping starts
            self.log_to_file("Scraping 3 websites started")
            # self.scrape_gundeals(ucp = upc)
            try:
                #t1 = Thread(target=self.scrape_gundeals, args=(upc,))
                #t2 = Thread(target=self.scrape_gunengine, args=(upc, product_type))
                t3 = Thread(target=self.scrape_wikiarms, args=(upc, product_type))
                #t1.start()
                #t2.start()
                t3.start()
                #t1.join()
                #t2.join()
                t3.join()
                # self.scrape_barcodelookup(upc)

                ###
                # self.scrape_wikiarms(upc)
                ###

                self.log_to_file("Scraping 3 websites finished")
                self.log_to_file("Checking duplicates")
                upcs_products = self.remove_duplicates(upc, self.upcs_products)

                json_upcs_products[upc.replace("'", '')] = [l for l in upcs_products]

                with open(f"tmp/json_upcs_prices_{self.ucp_csv_path.split('/')[-1].split('.')[0]}.json",
                          'w') as outfile:
                    json.dump(json_upcs_products, outfile)

                bucket.upload_file(f"tmp/json_upcs_prices_{self.ucp_csv_path.split('/')[-1].split('.')[0]}.json",
                                   f"data/json_upcs_prices_{self.ucp_csv_path.split('/')[-1].split('.')[0]}.json")

                # print("len : ", len(upcs_products))
                if not len(upcs_products) == 0:
                    scraped_prices = list(zip(*upcs_products))[-1]
                    scraped_prices = np.array(scraped_prices, dtype=np.float64)
                    target = np.abs(np.min([np.mean(scraped_prices), np.median(scraped_prices)]))
                    diff_perc = np.abs(round(target / float(price) - 1, 3))
                    diff_amount = np.abs(price - target)
                elif not self.failed:
                    self.log_to_file(
                        f"Target price and difference price will be inserted as N/A. No prices were scraped.")
                    scraped_prices = []
                    target = 'N/A'
                    diff_perc = 'N/A'
                    diff_amount = 'N/A'
                else:
                    self.log_to_file(
                        f"There was a fatal issue initiating one of the driver. Nothing will be inserted for upc {upc} and scraping will be resumed for another session.")
                    continue

                with open(self.ucp_csv_path) as inf:
                    reader = csv.reader(inf.readlines())

                with open(self.ucp_csv_path, 'w') as f:
                    writer = csv.writer(f)
                    for i, line in enumerate(reader):
                        # print(line)
                        if i == 0:
                            writer.writerow(line)
                            continue
                        if line[0] == upc:
                            # self.log_to_file(f"inserting stats for upc {upc}...")
                            # self.log_to_file("target price : ", target)
                            # self.log_to_file("difference percentage : ", diff_perc)
                            # self.log_to_file("difference amount : ", diff_amount)
                            self.log_to_file(f"Target price : {target} inserted for the price {price}")
                            # print("processed : ", True)
                            # line[4] = 1
                            if target != 'N/A':
                                line[5] = round(target, 3)
                                line[6] = diff_perc
                                line[7] = round(diff_amount, 3)
                            else:
                                line[5] = target
                                line[6] = diff_perc
                                line[7] = diff_amount
                            writer.writerow(line)
                            # print(line)
                            # break
                        else:
                            writer.writerow(line)
                    writer.writerows(reader)

                bucket.upload_file(self.ucp_csv_path, 'data/' + self.ucp_csv_path.split('/')[-1])
                self.log_to_file(
                    f"Finished processing upc {upc} with target price : {target} and difference percentage : {diff_perc}")

            except Exception as e:
                er = traceback.format_exc()
                self.log_to_file("A major problem occured in one of the scrapers : " + str(er))
                # print("A major problem occured in one of the scrapers : " + str(e))

            bucket.upload_file("tmp/logs.txt", "data/logs.txt")

            return upcs_products

    def remove_duplicates(self, ucp, upcs_products):
        if len(upcs_products) > 0:
            new_lst = [t for t in tuple((set(tuple(i) for i in upcs_products)))]
            print(
                f"{len(upcs_products) - len(new_lst)} duplicated products removed from {len(upcs_products)} products for ucp {ucp}.")
        else:
            self.log_to_file(f"upcs_products is empty. 0 products scraped from the 3 websites for upc {ucp}")
            new_lst = []

        return new_lst


#app = Flask(__name__)

#@app.route("/")
def main():
    warnings.filterwarnings("ignore")
    # logging.basicConfig(level=self.log_to_file)

    open("tmp/logs.txt", "w").close()
    print("downloading chromedriver")
    #s3 = boto3.client('s3', aws_access_key_id=config.ACCESS_ID, aws_secret_access_key=config.ACCESS_KEY)
    #s3.download_file(config.BUCKET_NAME, 'layers/chromedriver', 'tmp/chromedriver')
    #s3.download_file(config.BUCKET_NAME, 'layers/headless-chromium', 'tmp/headless-chromium')
    try:
        print(os.listdir('tmp'))
    except:
        print("nthing tmp")
    #os.chmod("tmp/chromedriver", 0o777)
    #os.chmod("tmp/headless-chromium", 0o777)

    scraper = Scraper(barcodelookup_url=config.barcodelookup_url, gunengine_url=config.gunengine_url,
                      gundeals_url=config.gundeals_url, wikiarms_url=config.wikiarms_url)
    r = scraper.scrape_all()
    return r


if __name__ == "__main__":
    main()
    #serve(app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080))))
