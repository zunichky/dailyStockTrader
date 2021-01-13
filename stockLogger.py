import datetime
from logging import currentframe
import stock

import time
from prettytable import PrettyTable
import config
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import brokerClient
import dbConnection


#CHANGEME FOR REAL TRADING
logging.getLogger().addHandler(logging.StreamHandler())
log_formatter = logging.Formatter(fmt='%(asctime)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
logFile = 'logs//db.log'
my_handler = TimedRotatingFileHandler(logFile,
                                       when="h",
                                       interval=1,
                                       backupCount=12)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)
app_log = logging.getLogger('database')
app_log.setLevel(logging.INFO)
app_log.addHandler(my_handler)

def updateWatchStocks(currentStocksWatching):
    updatedStocksToWatch = []
    newStocksToWatch = config.Settings.getWatchStocks()
    for newStockTicker in newStocksToWatch:
        found = False
        for currentStock in currentStocksWatching:
            if (newStockTicker.upper() == currentStock.symbol):
                updatedStocksToWatch.append(currentStock)
                currentStocksWatching.remove(currentStock)
                found = True
                continue
        if found == False:
            updatedStocksToWatch.append(stock.Stock(newStockTicker.upper()))
    return updatedStocksToWatch 

def main():
    config.Settings.load("F:\\My Documents\\Code\\PennyStockTrading\\config.ini")
    token_path = config.Settings.config.get("tdAccountSettings", "tokenPath" )
    api_key = config.Settings.config.get("tdAccountSettings", "apiKey" )
    redirect_uri = config.Settings.config.get("tdAccountSettings", "redirectUri" )

    dbConnection.PostgreSQL.setup()

    brokerClient.Client.authorize()

    stocksToWatch = []
    for i in config.Settings.getWatchStocks():
        stocksToWatch.append(stock.Stock(i.upper()))

    while (True):
        stockPriceRawData = brokerClient.Client.getQuotes()        
        insert_query = "INSERT INTO rawstockdata (timestamp, rawjson) VALUES ('" + datetime.now().strftime("%Y-%m-%d %H:%M:%S")  + "','" + str(stockPriceRawData).replace("'", '"').lower() + "')"
        if (dbConnection.PostgreSQL.insert(insert_query) == True):
            app_log.info("Db Insert successful")
        else:
            app_log.info("Failed DB Insert. " + str(stockPriceRawData))

        #get data every .7 seconds
        time.sleep(.7)

        if (config.Settings.isUpdated() == True):
            app_log.info("Configure change detected")
            newStocksToWatch = updateWatchStocks(stocksToWatch)
            if (len(newStocksToWatch) > 0):
                stocksToWatch = newStocksToWatch
                

if __name__ == "__main__":
    main()
