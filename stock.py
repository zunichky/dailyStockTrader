from collections import deque
from config import Settings
import logging
from prettytable import PrettyTable
import brokerClient
import liveStockData
import time
import datetime

class Stock:
    
    def __init__(self, ticker):
        self.symbol = ticker
        self.currentPrice = 0.0
        self.bid = 0.0
        self.ask = 0.0
        self.highPrice = 0.0
        self.highPriceCounter = 0.0
        self.lowPrice = 0.0
        self.lowPriceCounter = 0.0
        self.recentPrices = deque(maxlen=Settings.config.getint("default", "recentPriceLength", fallback=20 ))
        self.triggered = False
        self.purchasePrice = 0.0
        self.steadyCount = 0.0
        #1 for up, 0 f or down
        self.lastUpdated = 0
        self.app_log = logging.getLogger('root')
        self._lastUpdateTime = ""
        self._recentPrices = []

    def getSwingPercentage(self, highPrice, lowPrice):
        if (highPrice == lowPrice):
            return 0
        try:
            return  ((highPrice - lowPrice) / highPrice) * 100.0
        except ZeroDivisionError:
            return 0
    
    def average(lst): 
        return sum(lst) / len(lst) 

    def updateRecentPriceList(self):
        newPrice = self._getNewStockPrice()
        self._recentPrices.append(newPrice)

    def updatePrice(self, price):
        self.currentPrice = float(price)
        self.recentPrices.append(self.currentPrice)
        recentPricesSorted = sorted(self.recentPrices)

        if (self.highPrice == 0 or self.lowPrice == 0):
            self.highPrice = self.currentPrice
            self.lowPrice = self.currentPrice
            return

        if (self.currentPrice > self.highPrice ):
            self.steadyCount = 0
            self.lastUpdated = 1
            self.highPriceCounter = self.highPriceCounter + 1
            self.lowPriceCounter = 0
        elif (self.currentPrice < self.lowPrice ):
            self.steadyCount = 0
            self.lastUpdated = 0
            self.lowPriceCounter = self.lowPriceCounter + 1
            self.highPriceCounter = 0
        else:
            self.steadyCount = self.steadyCount + 1
        
        # If triggered, we don't want to remove high price
        if (self.triggered):
            if (self.highPrice < recentPricesSorted[-1]):
                self.highPrice = recentPricesSorted[-1]
        else:
            self.highPrice = recentPricesSorted[-1]
        
        self.lowPrice = recentPricesSorted[0]

        if (self.triggered):
            if (self.highPrice == self.currentPrice):
                self.lowPrice = self.currentPrice
            self._sellTrigger()
        else:
            #check to make sure we have a few prices logged
            if (len(self.recentPrices) > Settings.config.getfloat("default", "minimumStocksInQueue", fallback=0 )):
                self._buyTrigger()

    def printStockData(self):
        table = PrettyTable()
        table.field_names = ["Stock", "High", "Cur", "Low", "% Change", "Low Count", "High Count", "Steady Count"]
        table.add_row([self.symbol, self.highPrice, self.currentPrice,
        self.lowPrice, self.getSwingPercentage(self.highPrice, self.lowPrice), self.lowPriceCounter, 
        self.highPriceCounter, self.steadyCount])
        self.app_log.info(table)

    def _buyTrigger(self):
        swingPercent = self.getSwingPercentage(self.highPrice, self.lowPrice)
        
        #buy if stock went up > 1.75% anf high counter
        if (    self.lastUpdated == 1 
            and swingPercent > Settings.config.getfloat("buySettings", "swingPercent", fallback=2 )
            and self.highPriceCounter >= Settings.config.getfloat("buySettings", "highPriceCounter", fallback=2 )
            ):
           
            self.triggered = True
            return

        #reset if we have been declining
        elif (  self.lastUpdated == 0 
            and swingPercent > Settings.config.getfloat("resetSettings", "swingPercent", fallback=1.70 )
            and self.lowPriceCounter >= Settings.config.getfloat("resetSettings", "declinePriceCounter", fallback=3.0 )
            ):

            self.resetData("_buyTrigger Decrease")

        #reset if a lot in a row have been declining
        elif (self.lowPriceCounter >= Settings.config.getfloat("resetSettings", "declineCounter", fallback=10 )):
            self.resetData("_buyTrigger lowPriceCounter >= " + str(Settings.config.get("resetSettings", "declineCounter", fallback=10 )))
        
        #Reset if we have been slowly increasing, but haven't hit the percent threshold
        elif (self.highPriceCounter >= Settings.config.getfloat("resetSettings", "increaceCounter", fallback=12 )):
            self.resetData("_buyTrigger highPriceCounter >= " + str(Settings.config.get("resetSettings", "increaceCounter", fallback=12 )))
        
        #reset on steady count
        elif (self.steadyCount >= Settings.config.getfloat("resetSettings", "steadyCount", fallback=20 )):
            self.resetData("_buyTrigger Steady Count")
        
        #If we have an increase but then go to steady, reset the high counter
        elif (self.steadyCount >= Settings.config.getfloat("buySettings", "steadyReset", fallback=5 ) and self.highPriceCounter > 0):
            self.app_log.info("Restting high price counter from steady ")
            self.highPriceCounter = 0
        
        self.triggered = False

    def _sellTrigger(self):
        swingPercent = self.getSwingPercentage(self.highPrice, self.lowPrice)
        plPercent = self.getSwingPercentage(self.currentPrice, self.purchasePrice)
        
        #sell if we are down 1.7%
        if ( plPercent < Settings.config.getfloat("sellSettings", "maxLossPercent", fallback=-1.5 )):
            self.triggered = False
            self.resetData("_sellTrigger P/L Loss. Set at: " + str(Settings.config.getfloat("sellSettings", "maxLossPercent", fallback=-1.5 )))

        #sell on stock going down 2% from high
        elif ( self.lastUpdated == 0 
            and swingPercent > Settings.config.getfloat("sellSettings", "swingPercentFromHigh", fallback=2 ) 
            and self.lowPriceCounter >= Settings.config.getfloat("sellSettings", "lowPriceCounter", fallback=1 )  
            ):
            
            self.triggered = False
            #Resetting values after a trigger.
            self.resetData("_sellTrigger Decrease")
        
        #Sell on profits
        elif ( plPercent > Settings.config.getfloat("sellSettings", "percentGained", fallback=5 ) ):
            self.triggered = False
            #Resetting values after a trigger.
            self.resetData("_sellTrigger P/L Profit. Set at: " + str(Settings.config.getfloat("sellSettings", "percentGained", fallback=5 )))
        
        #sell on stock staying steady
        elif (self.steadyCount >= Settings.config.getfloat("sellSettings", "steadyCount", fallback=20 )):
            self.triggered = False
            self.resetData("_sellTrigger Steady Count")
    
    def _getNewStockPrice(self):
        if (Settings.config.getboolean("default", "pullFromDB", fallback=False) == True):
            #get data from db (simulation)
            if (self._lastUpdateTime == ""):
                self._lastUpdateTime = Settings.config.get("simulationSettings", "startTime" )
            else:
                self._lastUpdateTime = self._lastUpdateTime + datetime.timedelta(seconds = Settings.config.getfloat("default", "refreshRate"))
            jsonResponse = brokerClient.Client.getQuotes( pullFromDb=True, time=self._lastUpdateTime )
        else:
            #get live stock data from internet
            jsonResponse = brokerClient.Client.getQuotes( )

        currentData = liveStockData.LiveStockData(jsonResponse, ticker = self.symbol, quote=True)
        if (currentData.isValid()):
            #self.updatePrice(currentData.currentPrice)
            return currentData.currentPrice
        else:
            self.app_log.info("Invalid Data")
            self.app_log.info(jsonResponse)
            return 0

    def confirmPurchase(self, purchasePrice):
        if (float(purchasePrice) > 0):
            self.resetData("_buyTrigger Increase")
            self.purchasePrice = purchasePrice
        else:
            self.triggered = False

    def resetData(self, output):
        self.app_log.info("Restting stock high/low values from: " + output)
        self.printStockData()
        self.lowPrice = self.currentPrice
        self.highPrice = self.currentPrice
        self.recentPrices = deque(maxlen=Settings.config.getint("default", "recentPriceLength", fallback=20 ))
        self.lowPriceCounter = 0.0
        self.highPriceCounter = 0.0
        self.purchasePrice = 0.0
        self.steadyCount = 0.0

    def finalCheck(self):
        #want to check to make sure stock is still going up
        self.triggered = False
        #self.highPriceCounter = Settings.config.getfloat("buySettings", "highPriceCounter", fallback =2 ) - 1
        
        for x in range(Settings.config.getint("buySettings", "finalCheck", fallback=.2 )):
            #another stock read, if it went up, will trigger a buy
            time.sleep(Settings.config.getfloat("buySettings", "finalCheckSleep", fallback=.2 ))
            newPrice = self._getNewStockPrice()
            self.updatePrice(newPrice)
            #if (self.isTriggered()):
            #   return

    def shouldIPurchase(self):
        if (self.isTriggered()):
            if (Settings.config.getfloat("buySettings", "finalCheck", fallback=1 ) > 0 ):
                self.finalCheck()
            if (self.isTriggered()):
                self.printStockData()
                print("Should Buy Now")
                return True
            else:
                self.app_log.info("Final check failed on: " + self.symbol)
        return False

    def shouldISell(self):
        if (self.isTriggered() == False):
            print("Should Sell Now")
            return True
        else:
            return False

    def isTriggered(self):
        return self.triggered