from Broker.TdAmeritrade import TdAccount
from .AccountAbstract import *
import datetime
import json
import dbConnection
import utility
import tdAccount
from stock import Stock

class SimulationAccount(Account):

    def __init__(self, settings):
        super().__init__(settings)
        self._orderIdCounter = 0
    
    def _purchaseStock(self, ticker,  price = 0):
        stock = Stock(ticker)
        stock.symbol = ticker
        stock.currentPrice = price
        stock.purchasePrice = price
        stock.exchange = "UNKNOWN"
        self.currentHoldings.append(stock)
    
    def purchaseStockMarket(self, ticker, shares = 1, price = 0):
        self._orderIdCounter = self._orderIdCounter + 1
        order = Order()
        order.orderId = self._orderIdCounter
        order.quantity = shares
        order.status = results["FILLED"]
        order.targetPrice = price
        self._purchaseStock(ticker, price)
        print("Purchase fake: " + ticker )
        return order
    
    def purchaseStockLimit(self, ticker, shares, price ):
        return self.purchaseStockMarket(ticker, shares = shares, price = price)

    def _sellStock(self, ticker, price = 0):
        for i in range(len(self.currentHoldings)):
            print(self.currentHoldings[i].symbol)
            if (self.currentHoldings[i].symbol == ticker ):
                self.pl = self.pl + utility.getDifferencePercentage(float(self.currentHoldings[i].currentPrice), float(price) )
                del self.currentHoldings[i]
                break
    
    def sellStockMarket(self, ticker, shares = 1, price = 0):
        for x in self.currentHoldings:
            if (x.symbol == ticker):
                shares = x.sharesHeld
                break
        self._orderIdCounter = self._orderIdCounter + 1
        order = Order()
        order.orderId = self._orderIdCounter
        order.quantity = shares
        order.status = results["FILLED"]
        order.targetPrice = price
        order.sellPrice = price
        self._sellStock(ticker, price)
        print("Sell fake: " + ticker)
        return order
    
    def sellStockLimit(self, ticker, shares, limitPrice = 0):
        return self.sellStockMarket(ticker, shares = shares, price=limitPrice)

    def doIOwnThisStock(self, ticker):
        for y in self.currentHoldings:
            if (y.symbol == ticker):
                return True
        return False
    
    def getAccountBalance(self):
        print("$100 Fake")
    
    def getCurrentHoldings(self):
        return self.currentHoldings
    
    def updateAccountBalance(self):
        self.cashBalance = 1
        self.availableFunds = 1
        self.buyingPower = 1
        self.dayTradingBuyingPower = 1

    def updateCurrentHoldings(self):
        #list of stock classes
        self.currentHoldings = []

    def updateCurrentOrders(self):
        #lsit of order classes
        self.currentOrders = []

class SimulationBroker(Broker):
    _token_path = ""
    _api_key = ""
    _redirect_uri = ""
    account = ""
    pullFromDb = True
    broker = ""
    
    def __init__(self, pullFromDb, broker = ""):
        self.pullFromDb = pullFromDb
        self.broker = broker 
    
    def newAccount(self, settings):
        self.account = SimulationAccount(settings)
    
    def addBroker(self, broker):
        self.broker = broker

    def getQuote(self, ticker, time=""):
        stockList = self.getQuotes([ticker], time)
        for x in stockList:
            if (x.symbol == ticker):
                return x
        return ""

    def getQuotes( self, tickerList, time=""):
        if (self.pullFromDb == True):
            if (dbConnection.PostgreSQL.isInitialized == False):
                dbConnection.PostgreSQL.isInitialized.setup()
                
            #strftime("%Y-%m-%d %H:%M:%S")'
            time2 = time.strftime("%Y-%m-%d %H:%M:%S")
            time1 = (time - datetime.timedelta(milliseconds= 2500)).strftime("%Y-%m-%d %H:%M:%S")
            selectQuery = "SELECT rawjson, key FROM public.rawstockdata WHERE timestamp BETWEEN '{}' AND '{}'".format(time1, time2)
            data = dbConnection.PostgreSQL.select(selectQuery)
            if (len(data) > 0):
                x = json.dumps(data[-1][0])
                y = json.loads(x)
                return self.parseQuote(y)
            return ""
        else:
            return self.broker.getQuotes(tickerList, time)
    
    def parseQuote(self, json):
        items = ""
        stockList = []
        try:
            items = json.items()
        except Exception as ex:
            print("invalid JSON")
            return stockList
        
        for (k, v) in items:
            curStock = Stock(k)
            try:
                curStock.symbol = v['symbol'].upper()
                curStock.currentPrice = v["lastPrice"]
                curStock.exchange = str(v["exchangeName"]).upper()
            except:
                    try:
                        curStock.currentPrice = v["lastprice"]
                        curStock.exchange = v["exchangename"].upper()
                    except:
                        print("Can't parse json quote for: " + curStock.symbol)
            if (curStock.isValid()):
                stockList.append(curStock)

        return stockList