import datetime
from logging import currentframe
import stock
import liveStockData
import fakeTrading
import time
from prettytable import PrettyTable
import config
import logging
from logging.handlers import TimedRotatingFileHandler
import datetime
import brokerClient
import dbConnection


#CHANGEME FOR REAL TRADING
account = fakeTrading.FakeAccount()
logging.getLogger().addHandler(logging.StreamHandler())
log_formatter = logging.Formatter('%(message)s')
logFile = 'logs//app.log'
my_handler = TimedRotatingFileHandler(logFile,
                                       when="h",
                                       interval=1,
                                       backupCount=12)
my_handler.setFormatter(log_formatter)
my_handler.setLevel(logging.INFO)
app_log = logging.getLogger('root')
app_log.setLevel(logging.INFO)
app_log.addHandler(my_handler)
lastUpdateTime = ""

def sorter(e):
    return e.symbol

def printStockData(stocksToWatch):
    table = PrettyTable()
    table.title = "Watch List"
    table.field_names = ["Stock", "High", "Cur", "Low", "% Change", "Low Count", "High Count", "Steady Count"]
    stocksToWatch.sort(key=sorter)
    for i in stocksToWatch:
        table.add_row([i.symbol, i.highPrice, i.currentPrice,
        i.lowPrice, i.getSwingPercentage(i.highPrice, i.lowPrice), i.lowPriceCounter, 
        i.highPriceCounter, i.steadyCount])
    app_log.info(table)

def processData(jsonResponse, curStock):
    currentData = liveStockData.LiveStockData(jsonResponse, ticker = curStock.symbol, quote=True)
    if (currentData.isValid()):
        if (currentData.isValidExchange()):
            curStock.updatePrice(currentData.currentPrice)
        else:
            app_log.info("Invalid Exchange for stock: " + currentData.symbol + " " + currentData.exchange)
    else:
        app_log.info("Invalid Data")
        app_log.info(jsonResponse)

    if (account.doIOwnThisStock(currentData.symbol) ):
        if (curStock.shouldISell() == True):
            account.sellStock( curStock )
            printStockData([curStock])

    elif (curStock.shouldIPurchase() == True):
        #TODO get the actual purchase price
        purchasePrice = account.purchaseStock(curStock )
        printStockData([curStock])
        curStock.confirmPurchase(purchasePrice)

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

    if (len(currentStocksWatching) > 0):
        #need to sell these stocks if holding
        app_log.info("check to sell:")
        for holding in currentStocksWatching:
            if (account.doIOwnThisStock(holding.symbol) ):
                account.sellStock(holding)
    return updatedStocksToWatch

def printAllInfo(stocksToWatch, c):
    now = datetime.datetime.now()
    if (config.Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
        current_time = lastUpdateTime
        if (config.Settings.config.getboolean("simulationSettings", "logToFile", fallback=True) == False):
            print(current_time)
            print("Today's PL %:" + str(account.pl))
            print("")
            return
    else:
        current_time = now.strftime("%m/%d/%y %I:%M:%S%p")

    app_log.info(current_time)
    printStockData(stocksToWatch)
    account.printHoldings(stocksToWatch)
    app_log.info("Today's PL %:" + str(account.pl))
    app_log.info("")
    app_log.info("Refreshing data in " + config.Settings.config.get("default", "refreshRate", fallback=5) + " seconds")
    app_log.info("")

def main():
    config.Settings.load("F:\\My Documents\\Code\\PennyStockTrading\\config.ini")
    token_path = config.Settings.config.get("tdAccountSettings", "tokenPath" )
    api_key = config.Settings.config.get("tdAccountSettings", "apiKey" )
    redirect_uri = config.Settings.config.get("tdAccountSettings", "redirectUri" )
    
    if (config.Settings.config.getboolean("default", "logDataToDB", fallback=False ) == True or
    config.Settings.config.getboolean("default", "pullFromDB", fallback=False ) == True):
        dbConnection.PostgreSQL.setup()

    brokerClient.Client.authorize()

    stocksToWatch = []
    for i in config.Settings.getWatchStocks():
        stocksToWatch.append(stock.Stock(i.upper()))

    global lastUpdateTime 
    lastUpdateTime = datetime.datetime.strptime(config.Settings.config.get("simulationSettings", "startTime"), "%Y-%m-%d %H:%M:%S")

   # updateTime = 0

    while (True):
        if (config.Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
            #get data from db (simulation)

            lastUpdateTime = lastUpdateTime + datetime.timedelta(seconds = config.Settings.config.getfloat("default", "refreshRate"))
            stockPriceRawData = brokerClient.Client.getQuotes( pullFromDb=True, time=lastUpdateTime )
        else:
            #get live stock data from internet
            stockPriceRawData = brokerClient.Client.getQuotes( )

        if (config.Settings.config.getboolean("default", "logDataToDB", fallback=False) == True):
            insert_query = "INSERT INTO rawstockdata (timestamp, rawjson) VALUES ('" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  + "','" + str(stockPriceRawData).replace("'", '"').lower() + "')"
            dbConnection.PostgreSQL.insert(insert_query)

        for x in stocksToWatch:
            processData(stockPriceRawData, x)
        
        printAllInfo(stocksToWatch,brokerClient.Client._c)

        #only sleep if we don't have any stocks being held
        #decrease sleep on stock buy
        if (config.Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
            if (lastUpdateTime >  datetime.datetime.strptime(config.Settings.config.get("simulationSettings", "endTime"), "%Y-%m-%d %H:%M:%S") ):
                app_log.info("Ending simulation")
                return
            time.sleep(config.Settings.config.getfloat("simulationSettings", "refreshRate", fallback=.1))
        else:
            time.sleep(config.Settings.config.getfloat("default", "refreshRate", fallback=5))

        if (config.Settings.isUpdated() == True):
            app_log.info("Configure change detected")
            newStocksToWatch = updateWatchStocks(stocksToWatch)
            if (len(newStocksToWatch) > 0):
                stocksToWatch = newStocksToWatch

if __name__ == "__main__":
    main()
