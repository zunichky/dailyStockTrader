import json
from liveStockData import LiveStockData
from accountClient import AccountClient
from prettytable import PrettyTable
import logging

class FakeAccount(AccountClient):
    
    def __init__(self):
        super().__init__()
        self.app_log = logging.getLogger('root')

    def purchaseStock(self, curStock):
        starterData = json.loads('{"service":"QUOTE","timestamp":1609883612701,"command":"SUBS","content":[{"key":"KEY","delayed":false,"BID_PRICE":0,"ASK_PRICE":0,"LAST_PRICE":0,"BID_SIZE":46,"ASK_SIZE":5,"ASK_ID":"P","BID_ID":"P","TOTAL_VOLUME":332515088,"LAST_SIZE":5,"TRADE_TIME":60811,"QUOTE_TIME":60812,"HIGH_PRICE":2.99,"LOW_PRICE":1.89,"BID_TICK":" ","CLOSE_PRICE":1.78,"EXCHANGE_ID":"q","MARGINABLE":true,"SHORTABLE":true,"QUOTE_DAY":18632,"TRADE_DAY":18632,"VOLATILITY":0.1592,"DESCRIPTION":"Jaguar Health, Inc. - Common Stock Status Alert: Deficient","LAST_ID":"P","DIGITS":4,"OPEN_PRICE":2.21,"NET_CHANGE":0.27,"HIGH_52_WEEK":2.99,"LOW_52_WEEK":0.185,"PE_RATIO":0.24,"EXCHANGE_NAME":"NASD","DIVIDEND_DATE":" ","IS_REGULAR_MARKET_QUOTE":true,"REGULAR_MARKET_LAST_PRICE":1.95,"REGULAR_MARKET_LAST_SIZE":1485,"REGULAR_MARKET_TRADE_TIME":57600,"REGULAR_MARKET_TRADE_DAY":18632,"REGULAR_MARKET_NET_CHANGE":0.17,"SECURITY_STATUS":"Normal","MARK":2.04,"QUOTE_TIME_IN_LONG":1609883612436,"TRADE_TIME_IN_LONG":1609883611910,"REGULAR_MARKET_TRADE_TIME_IN_LONG":1609880400868}]}')
        starterData["content"][0]["LAST_PRICE"] = curStock.currentPrice
        starterData["content"][0]["key"] = curStock.symbol
        purchasedStock = LiveStockData(starterData)
        if (purchasedStock.isValid()):
            self.app_log.info("Bought: " + curStock.symbol + " at $" + str(curStock.currentPrice))
            self.currentHoldings.append(purchasedStock)
            return curStock.currentPrice
        else:
            self.app_log.info("invalid stock initalization")
            return 0
    
    def sellStock(self, stock):
         for i in range(len(self.currentHoldings)):
             if (self.currentHoldings[i].symbol == stock.symbol ):
                self.pl = self.pl + stock.getSwingPercentage(float(stock.currentPrice), float(self.currentHoldings[i].currentPrice) )
                self.app_log.info("Sold: " + stock.symbol + " at: $" + str( stock.currentPrice)  )
                self.app_log.info("Purchased at: " + stock.symbol + " at: $" + str( self.currentHoldings[i].currentPrice)  )
                del self.currentHoldings[i]
                break
    
    def printHoldings(self, watchList):
        table = PrettyTable()
        table.title = "Holdings"
        table.field_names = ["Stock", "Purchase Price", "Current Price", "% Change"]
        for stock in watchList:
            if (stock.purchasePrice > 0):
                table.add_row([stock.symbol, str(stock.purchasePrice), stock.currentPrice, 
                str(self.getDifferencePercentage(stock.purchasePrice, stock.currentPrice ))])
        self.app_log.info(table)

    def getAccountBalance(self):
        raise NotImplementedError("Don't forget to implement")
    
    def getDifferencePercentage(self, purchasePrice, currentPrice):
        if (purchasePrice == currentPrice):
            return 0
        try:
            return  ((currentPrice - float(purchasePrice)) / currentPrice) * 100.0
        except ZeroDivisionError:
            return 0

    def doIOwnThisStock(self, ticker):
        for y in self.currentHoldings:
            if (y.symbol == ticker):
                return True
        return False

