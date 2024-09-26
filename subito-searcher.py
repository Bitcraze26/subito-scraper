#!/usr/bin/env python3.7

import argparse
import requests
from bs4 import BeautifulSoup, Tag
import json
import os
import platform
import requests
import re
import time as t
from datetime import datetime, time
import json

queries = dict()
apiCredentials = dict()
dbFile = "searches.tracked"
telegramApiFile = "telegram_api_credentials"
notify = True
# TELEGRAM API TOKEN = 8156605467:AAG72z8cEcWuLM65mlUi6G7ZRIjp1PA7WmM

import json

with open('config.ini', 'r') as f:
    config = json.load(f)

telegramToken = config['telegramToken']
telegramChatID = config['telegramChatID'] 
minPrice = config['minPrice']
maxPrice = config['maxPrice']
urlRicerca = config['urlRicerca']
nomeRicerca = config['nomeRicerca']
delayRicerca = config['delayRicerca'] # Usa getint per interi
ricercaContinua = config['ricercaContinua']

# Windows notifications
if platform.system() == "Windows":
    from win10toast import ToastNotifier
    toaster = ToastNotifier()


# load from file
def load_queries():
    '''A function to load the queries from the json file'''
    global queries
    global dbFile
    if not os.path.isfile(dbFile):
        return

    with open(dbFile) as file:
        queries = json.load(file)

def load_api_credentials():
    '''A function to load the telegram api credentials from the json file'''
    global apiCredentials
    global telegramApiFile
    if not os.path.isfile(telegramApiFile):
        return

    with open(telegramApiFile) as file:
        apiCredentials = json.load(file)


def print_queries():
    '''A function to print the queries'''
    global queries
    #print(queries, "\n\n")

    for search in queries.items():
        print("\nsearch: ", search[0])
        for query_url in search[1]:
            print("query url:", query_url)
            for url in search[1].items():
                for minP in url[1].items():
                    for maxP in minP[1].items():
                        for result in maxP[1].items():
                            print("\n", result[1].get('title'), ":", result[1].get('price'), "-->", result[1].get('location'))
                            print(" ", result[0])


# printing a compact list of trackings
def print_sitrep():
    '''A function to print a compact list of trackings'''
    global queries
    i = 1
    for search in queries.items():
        print('\n{}) search: {}'.format(i, search[0]))
        for query_url in search[1].items():
            for minP in query_url[1].items():
                for maxP in minP[1].items():
                    print("query url:", query_url[0], " ", end='')
                    if minP[0] !="null":
                        print(minP[0],"<", end='')
                    if minP[0] !="null" or maxP[0] !="null":
                        print(" price ", end='')
                    if maxP[0] !="null":
                        print("<", maxP[0], end='')
                    print("\n")

        i+=1

def refresh(notify):
    '''A function to refresh the queries

    Arguments
    ---------
    notify: bool
        whether to send notifications or not

    Example usage
    -------------
    >>> refresh(True)   # Refresh queries and send notifications
    >>> refresh(False)  # Refresh queries and don't send notifications
    '''
    global queries
    try:
        for search in queries.items():
            for url in search[1].items():
                for minP in url[1].items():
                    for maxP in minP[1].items():
                        run_query(url[0], search[0], notify, minP[0], maxP[0])
    except requests.exceptions.ConnectionError:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " ***Connection error***")
    except requests.exceptions.Timeout:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " ***Server timeout error***")
    except requests.exceptions.HTTPError:
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " ***HTTP error***")


def delete(toDelete):
    '''A function to delete a query

    Arguments
    ---------
    toDelete: str
        the query to delete

    Example usage
    -------------
    >>> delete("query")
    '''
    global queries
    queries.pop(toDelete)

def logs(message, time=True,log_file="log.txt"):
    if(time):
        current_time = datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        log_entry = f"[{current_time}]: {message}\n"
    else:
        log_entry = f"{message}\n"
    
    # Apre il file in modalità append (crea il file se non esiste)
    with open(log_file, 'a') as file:
        file.write(log_entry)

def run_query(url, name, notify, minPrice, maxPrice):
    '''A function to run a query

    Arguments
    ---------
    url: str
        the url to run the query on
    name: str
        the name of the query
    notify: bool
        whether to send notifications or not
    minPrice: str
        the minimum price to search for
    maxPrice: str
        the maximum price to search for

    Example usage
    -------------
    >>> run_query("https://www.subito.it/annunci-italia/vendita/usato/?q=auto", "query", True, 100, "null")
    '''
    query_log = datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " running query (\"{}\" - {})...".format(name, url)
    print(query_log)
    logs(query_log,False)

    products_deleted = False

    global queries
    page = requests.get(url)
    soup = BeautifulSoup(page.text, 'html.parser')

    product_list_items = soup.find_all('div', class_=re.compile(r'item-card'))
    msg = []

    for product in product_list_items:
        title = product.find('h2').string
        if title.lower().find(name.lower()) != -1: # se il titolo contiene la nostra stringa di ricerca
            try:
                price=product.find('p',class_=re.compile(r'price')).contents[0]
                # check if the span tag exists
                price_soup = BeautifulSoup(price, 'html.parser')
                if type(price_soup) == Tag:
                    continue
                #at the moment (20.5.2021) the price is under the 'p' tag with 'span' inside if shipping available
                price = int(price.replace('.','')[:-2])
            except:
                price = "Unknown price"

            link = product.find('a').get('href')

            # Usa regex per trovare l'ID prima di ".htm"
            match = re.search(r'-(\d+)\.htm', link)
            id_annuncio = match.group(1)

            sold = product.find('span',re.compile(r'item-sold-badge'))

            # check if the product has already been sold
            if sold != None:

                try:
                # if the product has previously been saved remove it from the file
                    if queries.get(name).get(url).get(minPrice).get(maxPrice).get(link):
                        del queries[name][url][minPrice][maxPrice][link]
                        products_deleted = True
                    continue
                except:
                    pass

            try:
                location = product.find('span',re.compile(r'town')).string + product.find('span',re.compile(r'city')).string
            except:
                print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " Unknown location for item %s @ %d" % (title, price))
                location = "Unknown location"
                        
            if minPrice == "null" or price == "Unknown price" or price>=int(minPrice):
                if maxPrice == "null" or price == "Unknown price" or price<=int(maxPrice):
                    if not queries.get(name):   # insert the new search
                        queries[name] = {url:{minPrice: {maxPrice: {link: {'title': title, 'price': price, 'location': location, 'id': id_annuncio}}}}}
                        print("\n" + datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " New search added:", name)
                        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " Adding result:", title, "-", price, "-", location)
                        tmp = datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + "\n\nNuovo annuncio trovato per "+name+":\n"+title+" @ "+str(price)+"€ - "+location+" - ("+id_annuncio+") --> "+link+'\n'
                        msg.append(tmp)
                        print("\n".join(msg))
                        print('\n{} nuovo articolo trovato. '.format(len(msg)))
                        send_telegram_messages(msg)
                        logs(msg)
                        msg=[]
                    else:   # add search results to dictionary
                        try:
                            if not queries.get(name).get(url).get(minPrice).get(maxPrice).get(link):   # found a new element
                                tmp = datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + "\n\nNuovo annuncio trovato per "+name+":\n"+title+" @ "+str(price)+"€ - "+location+" - ("+id_annuncio+") --> "+link+'\n'
                                msg.append(tmp)
                                print("\n".join(msg))
                                print('\n{} nuovo articolo trovato. '.format(len(msg)))
                                send_telegram_messages(msg)
                                logs(msg)
                                msg = []
                                queries[name][url][minPrice][maxPrice][link] ={'title': title, 'price': price, 'location': location, 'id': id_annuncio}
                        except:
                            pass

    ''' if len(msg) > 0:
        if notify:
            #if is_telegram_active():
            send_telegram_messages(msg)
            print("\n".join(msg))
            print('\n{} new elements have been found.'.format(len(msg)))
        save_queries()
    else:
        print('\nAll lists are already up to date.')

        # if at least one search was deleted updated the search file
        if products_deleted:
            save_queries()

    # print("queries file saved: ", queries)'''


def save_queries():
    '''A function to save the queries
    '''
    with open(dbFile, 'w') as file:
        file.write(json.dumps(queries))

def save_api_credentials():
    '''A function to save the telegram api credentials into the telegramApiFile'''
    with open(telegramApiFile, 'w') as file:
        file.write(json.dumps(apiCredentials))

def send_telegram_messages(messages):
    '''A function to send messages to telegram

    Arguments
    ---------
    messages: list
        the list of messages to send

    Example usage
    -------------
    >>> send_telegram_messages(["message1", "message2"])
    '''
    for msg in messages:
        request_url = "https://api.telegram.org/bot" + apiCredentials["token"] + "/sendMessage?chat_id=" + apiCredentials["chatid"] + "&text=" + msg
        requests.get(request_url)
        print('\n***MESSAGGIO TELEGRAM INVIATO***')

def in_between(now, start, end):
    '''A function to check if a time is in between two other times

    Arguments
    ---------
    now: datetime
        the time to check
    start: datetime
        the start time
    end: datetime
        the end time

    Example usage
    -------------
    >>> in_between(datetime.now(), datetime(2021, 5, 20, 0, 0, 0), datetime(2021, 5, 20, 23, 59, 59))
    '''
    if start < end:
        return start <= now < end
    elif start == end:
	    return True
    else: # over midnight e.g., 23:30-04:15
        return start <= now or now < end

if __name__ == '__main__':

    ### Setup commands ###

    load_queries()
    load_api_credentials()

    if urlRicerca is not None and nomeRicerca is not None:
        run_query(urlRicerca, nomeRicerca, False, minPrice if minPrice is not None else "null", maxPrice if maxPrice is not None else "null")
        print(datetime.now().strftime("%Y-%m-%d, %H:%M:%S") + " Query added.")
    # Telegram setup

    if telegramToken is not None and telegramChatID is not None:
        apiCredentials["token"] = telegramToken
        apiCredentials["chatid"] = telegramChatID
        save_api_credentials()

    ### Run commands ###

    print()
    save_queries()


    if ricercaContinua:
        while True:
                refresh(True)
                print()
                print(str(delayRicerca) + " seconds to next poll.")
                save_queries()
                t.sleep(int(delayRicerca))

# --addtoken "8156605467:AAG72z8cEcWuLM65mlUi6G7ZRIjp1PA7WmM" --addchatid 128931058 
# @ScrapingMeBot