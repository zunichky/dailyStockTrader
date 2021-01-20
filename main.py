from Broker.AccountAbstract import results
import datetime
from logging import currentframe
import stock
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
import math

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

def buyConfirmation(orderResult):
    if (orderResult == ""):
        app_log.info("orderReseult is blank")
        return False
    if (orderResult.status.value == results.WORKING.value 
        or orderResult.status.value == results.QUEUED.value):

        app_log.info("Trying to execute")
        time.sleep(.5)
        curOrder = broker.getOrder(orderResult.orderId)
        if (curOrder.orderId == orderResult.orderId):
            if (curOrder.status.value != results.FILLED.value 
                and curOrder.status.value != results.CANCELED.value):
                broker.cancelOrder(curOrder.orderId)
                app_log.info("Cancelling order: " + str(curOrder.orderId))
                return False
            else:
                app_log.info("Result on retry for order: " + str(curOrder.orderId) + " - " +  str(curOrder.status.value))
                return True
        app_log.info("Can't find order id in orders: " + str(orderResult.orderId))
        return False
    elif (orderResult.status.value != results.FILLED.value and orderResult.status.value != results.CANCELED.value):
        broker.cancelOrder(orderResult.orderId)
        app_log.info("Cancelling order: " + str(orderResult.orderId))
        return False
    elif (orderResult.status.value == results.CANCELED.value):
        app_log.info("Order cancelled by TD: " + str(orderResult.orderId))
        return False
    return True

def sellConfirmation(orderResult):
    if (orderResult == ""):
        app_log.info("orderReseult is blank")
        return False
    if (orderResult.status.value == results.WORKING.value 
        or orderResult.status.value == results.QUEUED.value):

        app_log.info("Trying to execute sell")
        time.sleep(.5)
        curOrder = broker.getOrder(orderResult.orderId)
        if (curOrder.orderId == orderResult.orderId):
            if (curOrder.status.value != results.FILLED.value 
                and curOrder.status.value != results.CANCELED.value):
                app_log.info("Order still not through: " + str(curOrder.orderId))
                return False
            else:
                app_log.info("Result on retry for order: " + str(curOrder.orderId) + " - " +  str(curOrder.status.value))
                return True
        app_log.info("Can't find order id in orders: " + str(orderResult.orderId))
        return False
    elif (orderResult.status.value != results.FILLED.value and orderResult.status.value != results.CANCELED.value):
        app_log.info("Order still not through: " + str(orderResult.orderId))
        return False
    elif (orderResult.status.value == results.CANCELED.value):
        app_log.info("Order cancelled by TD: " + str(orderResult.orderId))
        return False

    return True
def checkToSell(curStock):
    if (curStock.shouldISell() == True):
        result = broker.account.sellStockMarket( curStock.symbol, price=curStock.currentPrice )
        if (not sellConfirmation(result)):
            app_log.info("Couldn't Sell")
            return
        app_log.info("Sold: " + curStock.symbol + " at: $" + str( result.sellPrice) )
        app_log.info("Purchased: " + curStock.symbol + " at: $" + str(curStock.purchasePrice))
        curStock.purchasePrice = 0.0
        curStock.sharesHeld = 0
        printStockData([curStock])

def checkToBuy(curStock):
    if (curStock.shouldIPurchase() == True):
        orderResult = broker.account.purchaseStockMarket(curStock.symbol, shares = getMaxAmountOfShares(curStock.currentPrice), price = curStock.currentPrice )
        if (not buyConfirmation(orderResult)):
            app_log.info("Couldn't Buy")
            return
        curStock.confirmPurchase(orderResult.targetPrice)
        curStock.sharesHeld = orderResult.quantity
        app_log.info("Bought: " + curStock.symbol + " at $" + str(orderResult.targetPrice))
        printStockData([curStock])

def getMaxAmountOfShares(price):
    maxSpending = Settings.config.getfloat("buySettings", "priceStockPurchase")
    if (price > maxSpending):
        return 0
    return math.floor(maxSpending / price)

def updateWatchStocks(currentStocksWatching):
    #TODO this function needs to get looked ino
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
                broker.account.sellStockMarket(holding.symbol, price=holding.currentPrice)
                app_log.info("Sold: " + holding.symbol + " at: $" + str( holding.currentPrice)  )
                app_log.info("Purchased: " + holding.symbol + " at: $" + str(holding.purchasePrice)  )
                
    return updatedStocksToWatch


def printHoldingsFake(watchList):
    table = PrettyTable()
    table.title = "Holdings"
    table.field_names = ["Stock", "Purchase Price", "Shares", "P/L %"]
    for stock in watchList:
        if (stock.purchasePrice > 0):
            table.add_row([stock.symbol, str(stock.purchasePrice), stock.sharesHeld,
            str(utility.getDifferencePercentage(stock.purchasePrice, stock.currentPrice ))])
    app_log.info(table)

def printHoldingsReal( watchList):
    table = PrettyTable()
    broker.account.updateAccountBalance()
    table.title = "Equity: " + str(broker.account.equity) + " Bal: " + str(broker.account.cashBalance)
    table.field_names = ["Stock", "Purchase Price", "Shares",  "P/L %"]
    for stock in broker.account.getCurrentHoldings():
        for x in watchList:
            if (stock.symbol == x.symbol):
                stock.currentPrice = x.currentPrice
                x.purchasePrice = stock.purchasePrice
                break

        table.add_row([stock.symbol, str(stock.purchasePrice), stock.sharesHeld,
        str(utility.getDifferencePercentage(stock.purchasePrice, stock.currentPrice ))])    
    app_log.info(table)

def printAllInfo(stocksToWatch):
    now = datetime.datetime.now()
    if (Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
        current_time = lastUpdateTime
        if (Settings.config.getboolean("simulationSettings", "logToFile", fallback=True) == False):
            print(current_time)
            print("Today's PL %:" + str(broker.account.pl))
            print("Today's PL %:" + str(broker.account.pl))
            print("")
            return
    else:
        current_time = now.strftime("%m/%d/%y %I:%M:%S%p")

    app_log.info(current_time)
    printStockData(stocksToWatch)
    
    if (Settings.config.get("default", "account") == "fakeMoney"):
        printHoldingsFake(stocksToWatch)
    else:
        printHoldingsReal(stocksToWatch)

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

        stockPriceList = broker.getQuotes( listOfTickers, time=lastUpdate )
        
        for curStock in stocksToWatch:
            currentData = ""

            for x in stockPriceList:
                if (x.symbol == curStock.symbol):
                    currentData = x
                    break
            if (currentData != "" and currentData.isValid()):
                curStock.updateRecentPriceList(currentData.currentPrice)
            else:
                app_log.info("Invalid Data or Invalid Exchange: " + curStock.symbol + " Exchange: " + curStock.exchange)
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

    #TODO: Make this setting generic/not hardcoded
    accountType = Settings.config.get("default", "account", fallback="").strip().lower()
    #TODO change to isinstance()
    if (accountType == "fakemoney"):
        #TODO really need to rewrite the non db stuff. 
        # Possibility make broker and account info separate classes
        # We then would have a Broker, Account, StockData classes
        if (Settings.config.getboolean("default", "pullFromDb", fallback=False ) == True):
            broker = Broker.SimulationBroker.SimulationBroker(pullFromDb=True)
        else:
            brokerTd = Broker.TdAmeritrade.TdBroker(token_path, api_key, 
                redirect_uri, logToDb = Settings.config.get("default", "logDataToDB"))
            brokerTd.newAccount(0)
            broker = Broker.SimulationBroker.SimulationBroker(pullFromDb=False, broker=brokerTd)
        broker.newAccount(1)
    elif(accountType == "tdameritrade" ):
        broker = Broker.TdAmeritrade.TdBroker(token_path, api_key, redirect_uri,
            logToDb = Settings.config.get("default", "logDataToDB"))
        broker.newAccount(Settings.config.getint("tdAccountSettings", "accountId", fallback=0 ))
    else:
        app_log.info("Invalid Account in settings")
        return

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
        
        if (Settings.isUpdated() == True):
            app_log.info("Configure change detected")
            newStocksToWatch = updateWatchStocks(stocksToWatch)
            if (len(newStocksToWatch) > 0):
                stocksToWatch = newStocksToWatch
            else:
                stocksToWatch = []

        #add data to buffer until our refresh rate is hit
        updateBufferStocksData(stocksToWatch)

        endTimerMid = time.time()

        for x in stocksToWatch:
            x.updatePriceOffAverage()
            checkToSellOrBuy(x)

        printAllInfo(stocksToWatch)
        
        endTimer = time.time()
        print(endTimerMid -  startTimer)
        print(endTimer - startTimer )

        #Exit program if simulation is over
        if (Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
            if (lastUpdateTime >  datetime.datetime.strptime(Settings.config.get("simulationSettings", "endTime"), "%Y-%m-%d %H:%M:%S") ):
                app_log.info("Ending simulation")
                return
        elif (datetime.datetime.now().time() >  datetime.datetime.strptime(Settings.config.get("default", "endTime"), "%H:%M:%S").time() ):
            app_log.info("Ending simulation")
            #TODO sell all shares
            return


if __name__ == "__main__":
    main()
