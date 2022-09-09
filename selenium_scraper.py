import re
import pandas as pd
import os
import numpy as np
import math

import config
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import random
import logging
import traceback

from time import sleep

import itertools
from threading import Thread

import csv
import json

import requests

from datetime import datetime as dt

import warnings

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO)

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
api_url = config.url
username = config.username
password = config.password


class Scraper:
    def __init__(self, barcodelookup_url, gunengine_url, gundeals_url, chrome_version, ucp_csv_path, headless):
        self.upcs_products = []
        print("Setting up the main class")
        self.headless = headless
        print("The headless parameter is set to ", self.headless)
        self.barcodelookup_url = barcodelookup_url
        print("barcodelookup url : ", self.barcodelookup_url)
        self.gunengine_url = gunengine_url
        print("gunengine url : ", self.gunengine_url)
        self.gundeals_url = gundeals_url
        print("self.gundeals url : ", self.gundeals_url)
        self.chrome_version = chrome_version

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
            print("upc has len : ", len(upc))
            return "'" + upc + "'"

    # main function that sends data to the cloud via API
    def get_items(self):

        if not os.path.exists('data/file.txt'):
            open('data/file.txt', 'a').close()

        with open('data/file.txt', 'r') as f:
            lines = f.readlines()
            lines = [line.rstrip() for line in lines]

        print("lines : ", lines)
        if lines:
            timestamps = [dt.strptime(line, '%Y-%m-%d_%H-%M-%S') for line in lines]
            latest_timestamp = max(timestamps)
            print("latest df : ", latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S'))
            latest_df = pd.read_csv(f"data/results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv")
            target_prices = latest_df.target_price.values.tolist()
            print("target price : ", target_prices)
            price_difference_percents = latest_df.price_difference_percent.values.tolist()
            price_difference_amounts = latest_df.price_difference_amount.values.tolist()
            is_completed = all((not math.isnan(el1) or not math.isnan(el2) or not math.isnan(el3)) for el1, el2, el3 in zip(
                target_prices, price_difference_percents, price_difference_amounts))
            nothing = False
        else:
            nothing = True
            is_completed = True

        print("is completed : ", is_completed)
        if is_completed:
            if nothing:
                print("This is the first scraping session. First csv will be created.")
            else:
                print("All csvs are completed. Creating a new scraping session.")
            now = dt.now().strftime("%Y-%m-%d_%H-%M-%S")
            self.ucp_csv_path = f"data/results_{now}.csv"
        else:
            self.ucp_csv_path = f"data/results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv"
            print(f"The file results_{latest_timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.csv "
                  f"is not completed. Resuming scraping.")
            return

        to_return = []
        try:
            i = 1
            total = 1
            while i <= 1: #total:
                params = {
                    "page": i
                }
                print("current page : ", i)
                # get the response
                response = requests.get(api_url, auth=(username, password), params=params)
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
                    print("pages left : ", total - i)
                    i += 1
                    print("items pulled : ", len(to_return))

                    df = pd.DataFrame.from_dict(to_return)

                    df['target_price'] = ''
                    df['price_difference_percent'] = ''
                    df['price_difference_amount'] = ''

                    df = df.sample(frac=0.13)

                    print(self.ucp_csv_path)

                    df.to_csv(self.ucp_csv_path, index=False)

                else:
                    print(f'Error getting data' + str(response.json()))

            with open('data/file.txt', 'a') as f:
                f.write(now)

        except Exception as e:
            print(e)

        return len(df)

    def scrape_barcodelookup(self, ucp):
        """
        scrape barcodelookup websites
        """
        # iterate through all ucps
        # for ucp in self.ucps:
        scraper_name = 'barcodelookup'
        ucp = ucp.replace("'", "")
        stores_prices = []
        # ucp = '810048570348'
        # intiate the driver
        driver = self.init_driver()
        # get the url
        url = self.barcodelookup_url + str(ucp)
        print(f"[{scraper_name}] Getting products with UCP : {ucp} : {url}")
        try:
            driver.get(url)
        except:
            err = traceback.format_exc()
            print(f"There was an issue getting the url : {url}"
                  f"\nError Traceback: {err}")
            driver.quit()
            return
        sleep(random.uniform(1, 2))

        # get products elements
        try:
            els = driver.find_elements(By.XPATH, "//div[@class='store-list']/ol/li")
        except Exception as e:
            err = traceback.format_exc()
            print(f"There was an issue pulling [all products] with the ucp {ucp} from [barcodelookup] website."
                  f"\nError Traceback: {e}")
            driver.quit()
            return

        # iterate through all shops
        stores_prices = []
        for el in els:
            # get the price and store elements
            try:
                price = el.find_element(By.XPATH, './/span[2]').text
                store_href = el.find_element(By.XPATH, './/a').get_attribute("href")
                driver2 = self.init_driver()
                try:
                    driver2.get(store_href)
                except:
                    err = traceback.format_exc()
                    print(f"[{scraper_name}] There was an issue getting the store href : {store_href}"
                          f"\nError Traceback: {err}")
                    driver2.quit()
                    continue
                store_url = store_href
                i = 0
                while store_url == store_href and i < 4:
                    sleep(0.5)
                    store_url = driver2.current_url
                    i += 1
                driver2.quit()

            except Exception as e:
                price = None
                store_url = None
                err = traceback.format_exc()
                print(f"There was an issue pulling [a product] with the ucp {ucp} from [barcodelookup] website."
                      f"\nError Traceback: {e}")
                continue

            # save the price and store text
            # store = store.rstrip().lstrip().replace(':', '')
            price = float(price.replace('$', '').replace(',', ''))
            # price = 44.6
            # store_url = 'abc'
            stores_prices.append((store_url, price))
            # print("store name : ", store)
            print(f"[{scraper_name}] store url : ", store_url[:20] + '...')
            print(f"[{scraper_name}] price : ", price)

            # break

        # close the driver
        driver.close()
        # break
        # save products for this ucp
        self.upcs_products += stores_prices
        print(f"[{scraper_name}] finished.")
        # print(f"stores an prices with the ucp {ucp} for [barcodelookup] : {stores_prices}")

    def scrape_gunengine(self, ucp):
        # iterate through all ucps
        scraper_name = 'gunengine'
        cat_names = ['guns', 'ammo', 'parts']
        ucp = ucp.replace("'", "")
        stores_prices = []
        # ucp = '810048570348'
        # iterate through all possible categories
        for cat_name in cat_names:
            # print(f"Looking for ucp {ucp} in category {cat_name}")
            # intiate the driver
            driver = self.init_driver()
            # get the url
            url = self.gunengine_url + cat_name + '?q=' + str(ucp)
            print(f"[{scraper_name}] Getting products with UCP : {ucp} : {url} for category {cat_name}")
            try:
                driver.get(url)
            except:
                err = traceback.format_exc()
                print(f"There was an issue getting the url : {url}"
                      f"\nError Traceback: {err}")
                driver.quit()
                continue
            sleep(random.uniform(0.5, 1))

            # get products elements
            try:
                found = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/p').text
            except:
                sleep(random.uniform(1, 2))
                found = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/p').text

            # continue if 0 products found
            if int(re.search(r'\d+', found).group()) == 0:
                print(f"[{scraper_name}] 0 results found for ucp : {ucp}")
                driver.quit()
                continue

            # show all stores
            driver.find_element(By.XPATH, f'//*[@id="upc{ucp}"]/a').click()

            sleep(random.uniform(0.5, 1))
            # get stores elements
            try:
                variant_els = driver.find_elements(By.XPATH, "//div[@class='variant']")
            except Exception as e:
                err = traceback.format_exc()
                print(f"There was an issue pulling [all products] with the ucp {ucp} from [{scraper_name}] website."
                      f"\nError Traceback: {e}")
                driver.quit()
                continue
            # iterate through all shops
            stores_prices = []
            for variant_el in variant_els:
                # get the price and store elements
                try:
                    price = float(variant_el.find_element(
                        By.XPATH, "./div[1]/a[1]/span[@class='variant-price ']").text.replace('$', '').replace(',', ''))
                    store_href = variant_el.find_element(
                        By.XPATH, "./div[1]/a[1]").get_attribute('href')

                    driver2 = self.init_driver()
                    try:
                        driver2.get(store_href)
                    except:
                        err = traceback.format_exc()
                        print(f"There was an issue getting the store href : {store_href}"
                              f"\nError Traceback: {err}")
                        driver2.quit()
                        continue
                    store_url = store_href
                    i = 0
                    while store_url == store_href and i < 4:
                        sleep(0.5)
                        store_url = driver2.current_url
                        i += 1
                    driver2.quit()

                except Exception as e:
                    price = None
                    store_url = None
                    err = traceback.format_exc()
                    print(f"There was an issue pulling [a product] with the ucp {ucp} from [{scraper_name}] website."
                          f"\nError Traceback: {e}")
                    continue

                # save the price and store text
                # price = 44.6
                # store_url = 'abc'
                stores_prices.append((store_url, price))
                print(f"[{scraper_name}] store url : ", store_url[:20] + '...')
                print(f"[{scraper_name}] price : ", price)
                # break

        # close the driver
        driver.quit()
        # break
        # save productsUnnamed: 0 for this ucp
        self.upcs_products += stores_prices
        print(f"[{scraper_name}] finished.")
        # print(f"stores an prices with the ucp {ucp} for [gunengine] : {stores_prices}")

    def scrape_gundeals(self, ucp):
        """
        scrape barcodelookup websites
        """
        # iterate through all ucps
        scraper_name = 'gundeals'
        ucp = ucp.replace("'", "")
        stores_prices = []
        # ucp = '810048570348'
        # intiate the driver
        driver = self.init_driver()
        # get the url
        url = self.gundeals_url + str(ucp)
        print(f"[{scraper_name}] Getting products with UCP : {ucp} : {url}")
        try:
            driver.get(url)
        except:
            err = traceback.format_exc()
            print(f"There was an issue getting the url : {url}"
                  f"\nError Traceback: {err}")
            driver.quit()
            return
        sleep(random.uniform(1, 2))

        # get products elements
        try:
            els = driver.find_elements(By.XPATH, "//table[@id='price-compare-table']/tbody/tr")
        except Exception as e:
            err = traceback.format_exc()
            print(f"There was an issue pulling [all products] with the ucp {ucp} from [gundeals] website."
                  f"\nError Traceback: {e}")
            driver.quit()
            return

        # iterate through all shops
        stores_prices = []
        for el in els:
            # get the price and store elements
            if 'out of stock' in el.text.lower():
                print(f"[{scraper_name}] out of stock found")
                # print(el.text)
                break
            try:
                price = el.get_attribute('data-price')
                # store = el.find_element(By.XPATH, './/td[1]/div[1]/a[1]').get_attribute('data-ga-category')
                store_href = el.find_element(By.XPATH, './/td[1]/div[1]/a[1]').get_attribute('href')
                driver2 = self.init_driver()
                try:
                    driver2.get(store_href)
                except:
                    err = traceback.format_exc()
                    print(f"There was an issue getting the store href : {store_href}"
                          f"\nError Traceback: {err}")
                    continue

                store_url = store_href
                i = 0
                while store_url == store_href and i < 4:
                    sleep(0.5)
                    store_url = driver2.current_url
                    i += 1
                driver2.quit()
                price = float(price.replace('$', '').replace(',', ''))
            except Exception as e:
                price = None
                store_url = None
                err = traceback.format_exc()
                print(f"There was an issue pulling [a product] with the ucp {ucp} from [gundeals] website."
                      f"\nError Traceback: {e}")
                continue

            # save the price and store text
            # price = 44.6
            # store_url = 'abc'
            stores_prices.append((store_url, price))
            print(f"[{scraper_name}] store url : ", store_url[:20] + '...')
            print(f"[{scraper_name}] price : ", price)
            # break

        # close the driver
        driver.close()
        # break

        # save products for this ucp
        self.upcs_products += stores_prices
        print(f"[{scraper_name}] finished.")
        # print(f"stores an prices with the ucp {ucp} for [gundeals] : {stores_prices}")

    def init_driver(self, is_proxy=False):
        """
        initiate the undetected chrome driver
        """
        # chromedriver options
        options = uc.ChromeOptions()

        # set the chromedriver to headless mode
        if self.headless:
            # print("Scraping on headless mode.")
            options.add_argument('--headless')

        # set proxy
        if is_proxy:
            proxy = random.choice(config.proxies)
            options.add_argument(f'--proxy={proxy}')

        # devine the chrome version installed in OS
        chrome_version = config.chrome_version

        # intitate the driver instance with options and chrome version
        driver = uc.Chrome(options=options, version_main=chrome_version)

        return driver

    def load_ucps(self, ucp_csv_path):
        """
        yield each value of upcs and prices from saved API data (generator)
        """
        df = pd.read_csv(ucp_csv_path)
        upcs = df.upc.values.tolist()
        prices = df.price.values.tolist()
        target_prices = df.target_price.values.tolist()
        price_difference_percents = df.price_difference_percent.values.tolist()
        price_difference_amounts = df.price_difference_amount.values.tolist()

        for upc, price, target_price, price_difference_percent, price_difference_amount in zip(
                upcs, prices, target_prices, price_difference_percents, price_difference_amounts):
            if (math.isnan(target_price) or
                    math.isnan(price_difference_percent) or
                    math.isnan(price_difference_amount)):
                yield upc, price

    def scrape_all(self):
        """

        """
        # yielding upcs
        print("getting upcs and prices from the API ...")
        len = self.get_items()
        if len:
            print(f"Got {len}")
        else:
            print("an uncompleted csv file already exists")

        upcs_prices_generator = self.load_ucps(self.ucp_csv_path)
        for upc, price in upcs_prices_generator:
            print(f"scraping for upc {upc} and price {price} ...")
            self.upcs_products = []
            # Scraping starts
            print("Scraping 3 websites started")
            t1 = Thread(target=self.scrape_gundeals, args=(upc,))
            t2 = Thread(target=self.scrape_gunengine, args=(upc,))
            t3 = Thread(target=self.scrape_barcodelookup, args=(upc,))
            t1.start()
            t2.start()
            t3.start()
            t1.join()
            t2.join()
            t3.join()
            print("Scraping 3 websites finished")
            print("Checking duplicates")
            self.remove_duplicates(upc, self.upcs_products)

            scraped_prices = list(zip(*self.upcs_products))[-1]
            print("scraped prices : ", scraped_prices)

            scraped_prices = np.array(scraped_prices, dtype=np.float64)
            target = np.min([np.mean(scraped_prices), np.median(scraped_prices)])

            diff_perc = round(target / float(price) - 1, 3)
            diff_amount = price - target

            with open(self.ucp_csv_path) as inf:
                reader = csv.reader(inf.readlines())

            with open(self.ucp_csv_path, 'w') as f:
                writer = csv.writer(f)
                for i, line in enumerate(reader):
                    print(line)
                    if i == 0:
                        writer.writerow(line)
                        continue
                    if line[0] == upc:
                        print(f"inserting stats for upc {upc}...")
                        print("target price : ", target)
                        print("difference percentage : ", diff_perc)
                        print("difference amount : ", diff_amount)
                        # print("processed : ", True)
                        # line[4] = 1
                        line[4] = round(target, 3)
                        line[5] = diff_perc
                        line[6] = round(diff_amount, 3)
                        writer.writerow(line)
                        print(line)
                        # break
                    else:
                        writer.writerow(line)
                writer.writerows(reader)

            print(f"Finished processing upc {upc} with target price : {target} and difference percentage : {diff_perc}")

    def remove_duplicates(self, ucp, upcs_products):
        new_lst = [t for t in tuple((set(tuple(i) for i in upcs_products)))]
        print(f"{len(upcs_products) - len(new_lst)} products removed for ucp {ucp}.")
        upcs_products = new_lst

        self.upcs_products = upcs_products


scraper = Scraper(barcodelookup_url=config.barcodelookup_url, gunengine_url=config.gunengine_url,
                  gundeals_url=config.gundeals_url, chrome_version=config.chrome_version,
                  ucp_csv_path=config.ucp_csv_path, headless=config.headless)
# scraper.scrape_barcodelookup()
# scraper.scrape_gundeals()
scraper.scrape_all()
