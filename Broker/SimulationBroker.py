from Broker.TdAmeritrade import TdAccount
from .AccountAbstract import *
import datetime
import json
import dbConnection
from liveStockData import LiveStockData
import utility

class SimulationAccount(Account):

    def __init__(self, settings):
        super().__init__(settings)
    
    def purchaseStock(self, ticker,  limitPrice = 0):
        starterData = json.loads('{"service":"QUOTE","timestamp":1609883612701,"command":"SUBS","content":[{"key":"KEY","delayed":false,"BID_PRICE":0,"ASK_PRICE":0,"LAST_PRICE":0,"BID_SIZE":46,"ASK_SIZE":5,"ASK_ID":"P","BID_ID":"P","TOTAL_VOLUME":332515088,"LAST_SIZE":5,"TRADE_TIME":60811,"QUOTE_TIME":60812,"HIGH_PRICE":2.99,"LOW_PRICE":1.89,"BID_TICK":" ","CLOSE_PRICE":1.78,"EXCHANGE_ID":"q","MARGINABLE":true,"SHORTABLE":true,"QUOTE_DAY":18632,"TRADE_DAY":18632,"VOLATILITY":0.1592,"DESCRIPTION":"Jaguar Health, Inc. - Common Stock Status Alert: Deficient","LAST_ID":"P","DIGITS":4,"OPEN_PRICE":2.21,"NET_CHANGE":0.27,"HIGH_52_WEEK":2.99,"LOW_52_WEEK":0.185,"PE_RATIO":0.24,"EXCHANGE_NAME":"NASD","DIVIDEND_DATE":" ","IS_REGULAR_MARKET_QUOTE":true,"REGULAR_MARKET_LAST_PRICE":1.95,"REGULAR_MARKET_LAST_SIZE":1485,"REGULAR_MARKET_TRADE_TIME":57600,"REGULAR_MARKET_TRADE_DAY":18632,"REGULAR_MARKET_NET_CHANGE":0.17,"SECURITY_STATUS":"Normal","MARK":2.04,"QUOTE_TIME_IN_LONG":1609883612436,"TRADE_TIME_IN_LONG":1609883611910,"REGULAR_MARKET_TRADE_TIME_IN_LONG":1609880400868}]}')
        starterData["content"][0]["LAST_PRICE"] = limitPrice
        starterData["content"][0]["key"] = ticker
        purchasedStock = LiveStockData(starterData, fakeData = True)
        if (purchasedStock.isValid()):
            self.currentHoldings.append(purchasedStock)
            return limitPrice
        else:
            self.app_log.info("invalid stock initalization")
            return 0

    def sellStock(self, ticker, limitPrice = 0):
        for i in range(len(self.currentHoldings)):
            print(self.currentHoldings[i].symbol)
            if (self.currentHoldings[i].symbol == ticker ):
                self.pl = self.pl + utility.getDifferencePercentage(float(self.currentHoldings[i].currentPrice), float(limitPrice) )
                del self.currentHoldings[i]
                break

    def doIOwnThisStock(self, ticker):
        for y in self.currentHoldings:
            if (y.symbol == ticker):
                return True
        return False
    
    def getAccountBalance(self):
        print("$100 Fake")

class SimulationBroker(Broker):
    _token_path = ""
    _api_key = ""
    _redirect_uri = ""
    account = ""
    
    def __init__(self):
        pass
    
    def newAccount(self, settings):
        self.account = SimulationAccount(settings)

    def getQuotes( self,tickerList, time=""):
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
            return y
        return ""