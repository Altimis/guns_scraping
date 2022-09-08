import re
import pandas as pd
import os
import numpy as np

import config
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import random
import logging
import traceback

from time import sleep

import itertools
from threading import Thread

import requests

'''

upc = '850021104146'
#url = 'https://gun.deals/search/apachesolr_search/021291710485'
url = f'https://gun.deals/search/apachesolr_search/850021104146'
url = f'https://www.gunengine.com/guns?q=850021104146'
ucp = '022188701357'
url = f'https://www.barcodelookup.com/022188701357'

options = uc.ChromeOptions()
#options.add_argument('--headless')
#proxy = random.choice(config.proxies)
#options.add_argument(f'--proxy={proxy}')
chrome_version = config.chrome_version

driver = uc.Chrome(options=options, version_main=chrome_version)
try:
    #logging.info("getting url")
    driver.get(url)
    sleep(2)
    #1
    #els = driver.find_elements(By.XPATH, "//table[@id='price-compare-table']/tbody/tr")
    #2
    #found = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/p').text
    #print(found)
    #print(re.search(r'\d+', found).group())
    """
    if int(re.search(r'\d+', found).group()) == 0:
        print("no results")
        sleep(4444)
    driver.find_element(By.XPATH, f'//*[@id="upc{upc}"]/a').click()
    """
    #sleep(2)
    #els = driver.find_elements(By.XPATH, "//span[@class='variant-price ']")
    # 3
    els = driver.find_elements(By.XPATH, "//div[@class='store-list']/ol/li")
    print(len(els))
    prices = []
    for el in els:
        # 1
        """
        if 'out of stock' in el.text.lower():
            print("out of stock found")
            print(el.text)
            break
        """
        #1
        #price = el.get_attribute('data-price')
        # 2
        #price = float(el.text.replace('$', '').replace(',', ''))
        #print(price)
        #prices.append(price)
        # 3
        price = el.find_element(By.XPATH, './/span[2]').text
        print(price)
except Exception:
    err = "Couldn't get main url of artist with error : " + traceback.format_exc()
    logging.info(err)

"""
try:
    num_followers = driver.find_element(By.XPATH, '//strong[@data-e2e="followers-count"]').text
    num_following = driver.find_element(By.XPATH, '//strong[@data-e2e="following-count"]').text
except Exception as e:
    err_getting_foll = e
    num_following = ''
    num_followers = ''
"""

'''
class Scraper:


    def __init__(self, barcodelookup_url, gunengine_url, gundeals_url, chrome_version, ucp_csv_path, headless):
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
        print("Chrome version : ", self.chrome_version)
        self.ucps = self.load_ucps(ucp_csv_path)[:10]
        print(f"Got {len(self.ucps)} ucps.")
        self.upcs_products = {}

    def scrape_barcodelookup(self):
        """
        scrape barcodelookup websites
        """
        # iterate through all ucps
        for ucp in self.ucps:
            ucp = ucp.replace("'", "")
            #ucp = '810048570348'
            # intiate the driver
            driver = self.init_driver()
            # get the url
            url = self.barcodelookup_url + str(ucp)
            print(f"Getting products with UCP : {ucp} for [barcodelookup] website : {url}")
            try:
                driver.get(url)
            except:
                err = traceback.format_exc()
                print(f"There was an issue getting the url : {url}"
                      f"\nError Traceback: {err}")
                driver.quit()
                continue
            sleep(random.uniform(1, 2))

            # get products elements
            try:
                els = driver.find_elements(By.XPATH, "//div[@class='store-list']/ol/li")
            except Exception as e:
                err = traceback.format_exc()
                print(f"There was an issue pulling [all products] with the ucp {ucp} from [barcodelookup] website."
                      f"\nError Traceback: {e}")
                driver.quit()
                continue

            # iterate through all shops
            stores_prices = []
            for el in els:
                # get the price and store elements
                try:
                    price = el.find_element(By.XPATH, './/span[2]').text
                    store_href = el.find_element(By.XPATH, './/a').get_attribute("href")
                    print("store href : ", store_href)
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
                        sleep(1)
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
                #store = store.rstrip().lstrip().replace(':', '')
                price = float(price.replace('$', '').replace(',', ''))
                #price = 44.6
                #store_url = 'abc'
                stores_prices.append((store_url, price))
                #print("store name : ", store)
                print("store url : ", store_url)
                print("price : ", price)

                #break

            # close the driver
            driver.close()
            #break
        # save products for this ucp
        if ucp in self.upcs_products.keys():
            self.upcs_products[ucp] += stores_prices
        else:
            self.upcs_products[ucp] = stores_prices
        print(f"stores an prices with the ucp {ucp} for [barcodelookup] : {stores_prices}")



    def scrape_gunengine(self):
        # iterate through all ucps
        cat_names = ['guns', 'ammo', 'parts']
        for ucp in self.ucps:
            ucp = ucp.replace("'", "")
            #ucp = '810048570348'
            # iterate through all possible categories
            for cat_name in cat_names:
                print(f"Looking for ucp {ucp} in category {cat_name}")
                # intiate the driver
                driver = self.init_driver()
                # get the url
                url = self.gunengine_url + cat_name + '?q=' + str(ucp)
                print(f"Getting products with UCP : {ucp} for [gunengine] website : {url}")
                try:
                    driver.get(url)
                except:
                    err = traceback.format_exc()
                    print(f"There was an issue getting the url : {url}"
                          f"\nError Traceback: {err}")
                    driver.quit()
                    continue
                sleep(random.uniform(1, 2))

                # get products elements
                found = driver.find_element(By.XPATH, '//*[@id="main-content"]/div[2]/p').text

                # continue if 0 products found
                if int(re.search(r'\d+', found).group()) == 0:
                    print(f"0 results found for ucp : {ucp}")
                    driver.quit()
                    continue

                # show all stores
                driver.find_element(By.XPATH, f'//*[@id="upc{ucp}"]/a').click()

                sleep(random.uniform(1, 2))
                # get stores elements
                try:
                    variant_els = driver.find_elements(By.XPATH, "//div[@class='variant']")
                except Exception as e:
                    err = traceback.format_exc()
                    print(f"There was an issue pulling [all products] with the ucp {ucp} from [gunengine] website."
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
                        print("store href : ", store_href)

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
                            sleep(1)
                            store_url = driver2.current_url
                            i += 1
                        driver2.quit()

                    except Exception as e:
                        price = None
                        store_url = None
                        err = traceback.format_exc()
                        print(f"There was an issue pulling [a product] with the ucp {ucp} from [gunengine] website."
                              f"\nError Traceback: {e}")
                        continue

                    # save the price and store text
                    #price = 44.6
                    #store_url = 'abc'
                    stores_prices.append((store_url, price))
                    print("store url : ", store_url)
                    print("price : ", price)
                    #break

            # close the driver
            driver.quit()
            #break
        # save products for this ucp
        if ucp in self.upcs_products.keys():
            self.upcs_products[ucp] += stores_prices
        else:
            self.upcs_products[ucp] = stores_prices
        print(f"stores an prices with the ucp {ucp} for [gunengine] : {stores_prices}")


    def scrape_gundeals(self):
        """
        scrape barcodelookup websites
        """
        # iterate through all ucps
        for ucp in self.ucps:
            ucp = ucp.replace("'", "")
            #ucp = '810048570348'
            # intiate the driver
            driver = self.init_driver()
            # get the url
            url = self.gundeals_url + str(ucp)
            print(f"Getting products with UCP : {ucp} for [gundeals] website : {url}")
            try:
                driver.get(url)
            except:
                err = traceback.format_exc()
                print(f"There was an issue getting the url : {url}"
                      f"\nError Traceback: {err}")
                driver.quit()
                continue
            sleep(random.uniform(1, 2))

            # get products elements
            try:
                els = driver.find_elements(By.XPATH, "//table[@id='price-compare-table']/tbody/tr")
            except Exception as e:
                err = traceback.format_exc()
                print(f"There was an issue pulling [all products] with the ucp {ucp} from [gundeals] website."
                      f"\nError Traceback: {e}")
                driver.quit()
                continue

            # iterate through all shops
            stores_prices = []
            for el in els:
                # get the price and store elements
                if 'out of stock' in el.text.lower():
                    print("out of stock found")
                    print(el.text)
                    break
                try:
                    price = el.get_attribute('data-price')
                    #store = el.find_element(By.XPATH, './/td[1]/div[1]/a[1]').get_attribute('data-ga-category')
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
                    i = 1
                    while store_url == store_href and i < 4:
                        sleep(1)
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
                #price = 44.6
                #store_url = 'abc'
                stores_prices.append((store_url, price))
                print("store url : ", store_url)
                print("price : ", price)
                #break

            # close the driver
            driver.close()
            #break

        # save products for this ucp
        if ucp in self.upcs_products.keys():
            self.upcs_products[ucp] += stores_prices
        else:
            self.upcs_products[ucp] = stores_prices
        print(f"stores an prices with the ucp {ucp} for [gundeals] : {stores_prices}")

    def init_driver(self, is_proxy=False):
        """
        initiate the undetected chrome driver
        """
        # chromedriver options
        options = uc.ChromeOptions()

        # set the chromedriver to headless mode
        if self.headless:
            #print("Scraping on headless mode.")
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
        load upcs from saved API data
        """
        df = pd.read_csv(ucp_csv_path)
        upcs = df.upc.values.tolist()
        return upcs

    def scrape_all(self):
        """

        """
        # Scraping starts
        print("Scraping 3 websites started")
        t1 = Thread(target=self.scrape_gundeals)
        t2 = Thread(target=self.scrape_gunengine)
        t3 = Thread(target=self.scrape_barcodelookup)
        t1.start()
        t2.start()
        t3.start()
        t1.join()
        t2.join()
        t3.join()
        print("Scraping 3 websites finished")
        print("Checking duplicates")
        self.remove_duplicates(self.upcs_products)
        print("final results : ", self.upcs_products)

    def check_duplicates(self, upcs_products):
        for ucp, values in upcs_products.items():
            #store_price_list = list(zip(*values))
            print("len of store_price before removing duplicates : ", len(values))
            values = [next(t) for _, t in itertools.groupby(values, lambda x: x[0])]
            print("len of store_price after removing duplicates : ", len(values))

        self.upcs_products = upcs_products

    def remove_duplicates(self, upcs_products):
        for ucp, values in upcs_products.items():
            new_lst = [t for t in tuple((set(tuple(i) for i in values)))]
            print(f"{len(values)-len(new_lst)} products removed for ucp {ucp}.")
            #removed = [t for t in values if t not in new_lst]
            upcs_products[ucp] = new_lst
            #print(f"removed tuples for upc {ucp} : {removed}")

        self.upcs_products = upcs_products

    def compute_stats(self):
        self.targets = {}
        for upc, values in self.upcs_products.items():
            price_list = []
            for _, price in values:
                price_list.append(price)
            self.targets[upc] = np.min([np.mean(price_list), np.median(price_list)])

    def compute_difference(self):


scraper = Scraper(barcodelookup_url=config.barcodelookup_url, gunengine_url=config.gunengine_url,
                gundeals_url=config.gundeals_url, chrome_version=config.chrome_version,
                ucp_csv_path=config.ucp_csv_path, headless=config.headless)
#scraper.scrape_barcodelookup()
#scraper.scrape_gundeals()
scraper.scrape_all()