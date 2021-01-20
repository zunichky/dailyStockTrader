
from logging import NullHandler, error
from stock import Stock
from .AccountAbstract import *
from tda import auth, client
from tda.orders.equities import equity_buy_limit, equity_buy_market, equity_sell_limit, equity_sell_market
from tda.orders.common import Duration
from tda.utils import Utils
import json
import utility

class TdAccount(Account): 
    def __init__(self, settings, broker):
        super().__init__(settings)
        self.broker = broker

    def purchaseStockMarket(self, ticker, shares = 1, price = 0):
        result = Order()
        if (ticker != "" and shares > 1):
            order = equity_buy_market(ticker, shares).build()
            result = self._placeOrder(order)
            print("Purchase Real: " + ticker )
        return result
    
    def purchaseStockLimit(self, ticker, shares, price):
        result = Order()
        if (ticker != "" and shares > 1):
            order = equity_buy_limit(ticker, shares, price).set_duration(Duration.FILL_OR_KILL).build()
            result = self._placeOrder(order)
            print("Purchase Real: " + ticker )
        return result

    def _placeOrder(self, order):
        result = ""
        try:
            result = self.broker.executeOrder(order)
        except Exception as e:
            print(str(e))
        return result

    def sellStockMarket(self, ticker, shares = 0, price = 0):
        purchasePrice = 0
        for x in self.currentHoldings:
            if (x.symbol == ticker):
                if (shares == 0):
                    shares = x.sharesHeld
                purchasePrice = x.purchasePrice
                break

        order = equity_sell_market(ticker, shares)
        result = self._placeOrder(order)
        print("Sell Real: " + ticker)
        if (result != "" and result.orderId > 0):
            sellPrice = self.getSellingPrice(result.orderId)
            result.sellPrice = sellPrice
            self.pl = self.pl + (utility.getDifferencePercentage(purchasePrice, sellPrice))
        return result
    
    def getSellingPrice(self, orderId):
        return self.broker.getSellingPrice(orderId)

    def sellStockLimit(self, ticker, shares, limitPrice = 0):
        for x in self.currentHoldings:
            if (x.symbol == ticker):
                shares = x.sharesHeld
                break
        order = equity_sell_limit(ticker, shares, limitPrice)
        result = self._placeOrder(order)
        print("Sell Real: " + ticker)
        return result
    
    def doIOwnThisStock(self, ticker):
        for y in self.currentHoldings:
            if (y.symbol == ticker):
                return True
        return False

    def getCurrentHoldings(self):
        self.updateCurrentHoldings()
        return self.currentHoldings

    def updateAccountBalance(self):
        currentBalanceDict = None
        try:
            jsonRaw = json.loads(self.broker._c.get_account(self.settings).text)
            currentBalanceDict = responseHelper.getValue(jsonRaw, "securitiesAccount", "currentBalances")
        except Exception as ex:
            print("Couldn't update account balance")

        if (currentBalanceDict is not None):
            try:
                self.cashBalance = currentBalanceDict["cashBalance"]
                self.availableFunds = currentBalanceDict["availableFunds"]
                self.buyingPower = currentBalanceDict["buyingPower"]
                self.dayTradingBuyingPower = currentBalanceDict["dayTradingBuyingPower"]
                self.equity = currentBalanceDict["equity"]
            except Exception as ex:
                print ("Failed to update account balance")

    def updateCurrentHoldings(self):
        try:
            jsonRaw = json.loads(self.broker._c.get_account(self.settings, fields=client.Client.Account.Fields.POSITIONS).text)
            currentHoldingsJson = responseHelper.getValue(jsonRaw, "securitiesAccount", "positions")
            self.currentHoldings = responseHelper.parseCurrentHoldings(currentHoldingsJson)
        except Exception as ex:
            print("Couldn't update current holdings")

    def updateCurrentOrders(self):
        try:
            jsonRaw = json.loads(self.broker._c.get_account(self.settings, fields=client.Client.Account.Fields.ORDERS).text)
            listOfOrdersJson = responseHelper.getValue(jsonRaw, "securitiesAccount", "orderStrategies")
            self.currentOrders = responseHelper.parseCurrentOrders(listOfOrdersJson)
        except Exception as ex:
            print("Couldn't update current orders")

class TdBroker(Broker):
    _c = ""
    _token_path = ""
    _api_key = ""
    _redirect_uri = NullHandler
    account = ""

    def __init__(self,  tokenPath, apiKey, redirectUri, logToDb = False):   
        self._token_path = tokenPath
        self._api_key = apiKey
        self._redirect_uri = redirectUri
        self._logToDb = logToDb

        try:
            self._c = auth.client_from_token_file(self._token_path, self._api_key)
        except FileNotFoundError:
            from selenium import webdriver
            with webdriver.Chrome() as driver:
                self._c = auth.client_from_login_flow(
                    driver, self._api_key, self._redirect_uri, self._token_path)
    
    def newAccount(self, accountNumber):
        self.account = TdAccount(accountNumber, broker = self)

    def getQuotes( self , tickerList, time=""):
        returnDataLst = []
        try:
            returnData = self._c.get_quotes(tickerList).json()
            #parse into stock
            returnDataLst = responseHelper.parseQuote(returnData)
            #TODO REMOVE THIS DB CODE BELOW. Need to return the json so we can log db from main.py
            '''
            if (self._logToDb):
                insert_query = "INSERT INTO rawstockdata (timestamp, rawjson) VALUES ('" + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  + "','" + str(returnData).replace("'", '"').lower() + "')"
                if (dbConnection.PostgreSQL.insert(insert_query) == False):
                    print("Failed DB Insert. " + str(returnData))
            '''
        except:
            returnDataLst = []
        
        return returnDataLst
    
    def getQuote(self, ticker, time=""):
        quotes = self.getQuotes([ticker], time)
        for x in quotes:
            if (x.symbol.upper() == ticker.upper()):
                return x
        return ""

    def getOrder(self, orderId):
        jsonReponse = json.loads(self._c.get_order(orderId, self.account.settings).text)
        order = TdOrder()
        order.parseExecuteOrderResponse(jsonReponse, orderId)
        return order

    def executeOrder(self, order):
        orderResult = self._c.place_order(self.account.settings, order)
        orderId = Utils(self._c, self.account.settings).extract_order_id(orderResult)
        return self.getOrder(orderId)
    
    def cancelOrder(self,  orderNumber):
        self._c.cancel_order(orderNumber, self.account.settings)
    
    def getSellingPrice(self, orderId):
        jsonReponse = json.loads(self._c.get_order(orderId, self.account.settings).text)
        price = 0.0
        try:
            price = float(jsonReponse["orderActivityCollection"][0]["executionLegs"][0]["price"])
        except Exception as ex:
            print("Failed to get selling price")
        return price

class responseHelper():
    def getValue(data, *lookups):
        returnData = data
        for lookup in lookups:
            try:
                returnData = returnData[lookup]
            except Exception as ex:
                return None
        return returnData

    def parseKeys(json, keys):
        returnDict = {}
        for key in keys:
            try:
                returnDict[key] = json[key]
            except Exception as ex:
                returnDict[key] = None
        return returnDict
    
    def parseQuote(json):
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

    def parseCurrentHoldings(json):    
        positionsParsed = []
        if (json is not None):
            for curHolding in json:
                try:
                    x = Stock(curHolding["instrument"]["symbol"])
                    x.purchasePrice = curHolding["averagePrice"]
                    x.plPercent = curHolding["currentDayProfitLossPercentage"]
                    x.plDollars = curHolding["currentDayProfitLoss"]
                    x.sharesHeld = curHolding["longQuantity"]
                    positionsParsed.append(x)

                except Exception as ex:
                    print("Couldn't parse order")
                    print(curHolding)

        return positionsParsed

    def parseCurrentOrders(json):        
        ordersParsed = []
        if (json is not None):
            for orderJson in json:
                try:
                    order = TdOrder()
                    order.orderId = orderJson["orderId"]
                    order.status = client.Client.Order.Status["status"]
                    order.targetPrice = orderJson["cost"]
                    order.quantity = orderJson["quantity"]
                    order.quantityToBeFilled = orderJson["remainingQuantity"]
                    ordersParsed.append(order)
                except Exception as ex:
                    print("Couldn't parse order")
                    print(orderJson)
        return ordersParsed

class TdOrder(Order):
    def __init__(self):
        pass

    def parseExecuteOrderResponse(self, json, orderId):
        try:
            self.status = client.Client.Order.Status[json["status"]]
            self.orderId = orderId
            self.sellPrice = 0
        except Exception as ex:
            print(str(ex))
            self.status = None
            self.orderId = 0
