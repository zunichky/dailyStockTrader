import datetime
from logging import currentframe
import stock
import liveStockData
import time
from prettytable import PrettyTable
from config import Settings
import logging
from logging.handlers import TimedRotatingFileHandler
import datetime
import dbConnection
import Broker.SimulationBroker
import Broker.TdAmeritrade
import utility
import os

CONFIGPATH = "config.ini"
LOGGPATH = "logs"
#CHANGEME FOR REAL TRADING
broker = ""
#broker = Broker.SimulationBroker.SimulationBroker()
logging.getLogger().addHandler(logging.StreamHandler())
log_formatter = logging.Formatter('%(message)s')
if not os.path.exists(LOGGPATH):
    os.makedirs(LOGGPATH)
logFile = LOGGPATH + '//app.log'
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


def checkToSellOrBuy(curStock):
    if (broker.account.doIOwnThisStock(curStock.symbol) ):
        checkToSell(curStock)
    else:
        checkToBuy(curStock)

def checkToSell(curStock):
    if (curStock.shouldISell() == True):
        app_log.info("Sold: " + curStock.symbol + " at: $" + str( curStock.currentPrice)  )
        app_log.info("Purchased: " + curStock.symbol + " at: $" + str(curStock.purchasePrice))
        broker.account.sellStock( curStock.symbol, limitPrice=curStock.currentPrice )
        curStock.purchasePrice = 0.0
        printStockData([curStock])

def checkToBuy(curStock):
    if (curStock.shouldIPurchase() == True):
        #TODO get the actual purchase price
        rawJson = broker.getQuotes( curStock.symbol, time=lastUpdateTime )
        currentData = liveStockData.LiveStockData(rawJson, ticker = curStock.symbol)
        purchasePrice = broker.account.purchaseStock(currentData.symbol, limitPrice = currentData.currentPrice )
        printStockData([curStock])
        curStock.confirmPurchase(purchasePrice)
        app_log.info("Bought: " + curStock.symbol + " at $" + str(purchasePrice))


def processData(jsonResponse, curStock):
    currentData = liveStockData.LiveStockData(jsonResponse, ticker = curStock.symbol)
    if (currentData.isValid()):
        validExchanges = Settings.config.get("default", "validExchanges" )
        if (currentData.isValidExchange(validExchanges)):
            curStock.updatePrice(currentData.currentPrice)
        else:
            app_log.info("Invalid Exchange for stock: " + currentData.symbol + " " + currentData.exchange)
    else:
        app_log.info("Invalid Data")
        #app_log.info(jsonResponse)

    checkToSellOrBuy(curStock, broker)

def updateWatchStocks(currentStocksWatching):
    updatedStocksToWatch = []
    newStocksToWatch = Settings.getWatchStocks()
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
            if (broker.account.doIOwnThisStock(holding.symbol) ):
                broker.account.sellStock(holding.symbol, limitPrice=holding.currentPrice)
                app_log.info("Sold: " + holding.symbol + " at: $" + str( holding.currentPrice)  )
                app_log.info("Purchased: " + holding.symbol + " at: $" + str(holding.purchasePrice)  )
                
    return updatedStocksToWatch


def printHoldings(watchList):
    table = PrettyTable()
    table.title = "Holdings"
    table.field_names = ["Stock", "Purchase Price", "Current Price", "% Change"]
    for stock in watchList:
        if (stock.purchasePrice > 0):
            table.add_row([stock.symbol, str(stock.purchasePrice), stock.currentPrice, 
            str(utility.getDifferencePercentage(stock.purchasePrice, stock.currentPrice ))])
    app_log.info(table)

def printAllInfo(stocksToWatch):
    now = datetime.datetime.now()
    if (Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
        current_time = lastUpdateTime
        if (Settings.config.getboolean("simulationSettings", "logToFile", fallback=True) == False):
            print(current_time)
            print("Today's PL %:" + str(broker.account.pl))
            print("")
            return
    else:
        current_time = now.strftime("%m/%d/%y %I:%M:%S%p")

    app_log.info(current_time)
    printStockData(stocksToWatch)
    printHoldings(stocksToWatch)

    app_log.info("Today's PL %:" + str(broker.account.pl))
    app_log.info("")

def updateBufferStocksData(stocksToWatch):
    global lastUpdateTime
    updateRate = Settings.config.getfloat("default", "pullDataRate", fallback=1)
    pullFromDb = Settings.config.getboolean("default", "pullFromDB", fallback=False)
    refreshRate = Settings.config.getfloat("default", "refreshRate", fallback=5)
    
    if (pullFromDb):
        lastUpdate = lastUpdateTime
    else:
        lastUpdate = datetime.datetime.now()
    
    exitTime = lastUpdate + datetime.timedelta(seconds = (refreshRate))

    while (lastUpdate <= exitTime ):
        if (pullFromDb):
            time.sleep(Settings.config.getfloat("simulationSettings", "refreshRate", fallback=.1))
            lastUpdate = lastUpdate + datetime.timedelta(seconds = updateRate)
            lastUpdateTime = lastUpdate
        else:
            time.sleep(updateRate)
            lastUpdate = datetime.datetime.now()

        listOfTickers = []
        for x in stocksToWatch:
            listOfTickers.append(x.symbol)

        #if (pullFromDb == True):
            #get data from db (simulation)
        #    stockPriceRawJsonData = client.getQuotes( listOfTickers, time=lastUpdate )
        #else:
            #get live stock data from internet
        stockPriceRawJsonData = broker.getQuotes( listOfTickers, time=lastUpdate )
        
        for curStock in stocksToWatch:
            currentData = liveStockData.LiveStockData(stockPriceRawJsonData, ticker = curStock.symbol)
            if (currentData.isValid()):
                validExchanges = Settings.config.get("default", "validExchanges" )
                if (currentData.isValidExchange(validExchanges)):
                    curStock.updateRecentPriceList(currentData.currentPrice)
                else:
                    app_log.info("Invalid Exchange for stock: " + currentData.symbol + " Exchange: " + currentData.exchange)
            else:
                app_log.info("Invalid Data")
                #app_log.info(stockPriceRawJsonData)

def main():
    global broker
    Settings.load(CONFIGPATH)
    token_path = Settings.config.get("tdAccountSettings", "tokenPath" )
    api_key = Settings.config.get("tdAccountSettings", "apiKey" )
    redirect_uri = Settings.config.get("tdAccountSettings", "redirectUri" )
    
    if (Settings.config.getboolean("default", "logDataToDB", fallback=False ) == True or
    Settings.config.getboolean("default", "pullFromDB", fallback=False ) == True):
        dbConnection.PostgreSQL.setup()

    if (Settings.config.getboolean("default", "pullFromDB", fallback=False ) == True):
        broker = Broker.SimulationBroker.SimulationBroker()
        broker.newAccount(1)
    else:
        broker = Broker.TdAmeritrade.TdBroker(token_path, api_key, redirect_uri)
        broker.newAccount(132223)

    stocksToWatch = []
    for i in Settings.getWatchStocks():
        stocksToWatch.append(stock.Stock(i.upper()))
    
    datetime.datetime.strptime(Settings.config.get("default", "startTime"), "%H:%M:%S")

    now = datetime.datetime.now()
    startTime = datetime.datetime.strptime(Settings.config.get("default", "startTime"), "%H:%M:%S")
    
    while (now.time() < startTime.time()):
        time.sleep(5)
        app_log.info("Waiting to start")
        now = datetime.datetime.now()


    global lastUpdateTime 
    lastUpdateTime = datetime.datetime.strptime(Settings.config.get("simulationSettings", "startTime"), "%Y-%m-%d %H:%M:%S")

    startTimer = time.time()
    endTimer = time.time()

    while (True):
        startTimer = time.time()
        #add data to buffer until our refresh rate is hit
        updateBufferStocksData(stocksToWatch)

        endTimerMid = time.time()

        for x in stocksToWatch:
            x.updatePriceOffAverage()
            checkToSellOrBuy(x)

        '''
        ----- OLD WAY -------
        #now it's time to check the data
        stockPriceRawData = getStockQuotes()

        for x in stocksToWatch:
            processData(stockPriceRawData, x)
        ------------------------
        '''

        printAllInfo(stocksToWatch)

            
        if (Settings.isUpdated() == True):
            app_log.info("Configure change detected")
            newStocksToWatch = updateWatchStocks(stocksToWatch)
            if (len(newStocksToWatch) > 0):
                stocksToWatch = newStocksToWatch
            else:
                stocksToWatch = []
        
        endTimer = time.time()
        print(endTimerMid -  startTimer)
        print(endTimer - startTimer )

        #Exit program if simulation is over
        if (Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
            if (lastUpdateTime >  datetime.datetime.strptime(Settings.config.get("simulationSettings", "endTime"), "%Y-%m-%d %H:%M:%S") ):
                app_log.info("Ending simulation")
                return

if __name__ == "__main__":
    main()
