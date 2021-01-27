from collections import deque
from config import Settings
import logging
from prettytable import PrettyTable
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
        self.plDollars = 0
        self.plPercent = 0
        self.sharesHeld = 0
        self.steadyCount = 0.0
        #1 for up, 0 f or down
        self.lastUpdated = 0
        self.app_log = logging.getLogger('root')
        self._lastUpdateTime = ""
        self._recentPrices = []
        self._previousRecentPrices = []
        self.exchange = ""

    def getSwingPercentage(self, highPrice, lowPrice):
        if (highPrice == lowPrice):
            return 0
        try:
            return  ((highPrice - lowPrice) / highPrice) * 100.0
        except ZeroDivisionError:
            return 0
    
    def average(self, lst):
        if (len(lst) > 0 ):
            return sum(lst) / len(lst) 
        else:
            return 0

    def updateRecentPriceList(self, newPrice):
        if (newPrice > 0):
            self._recentPrices.append(newPrice)

    def updatePriceOffAverage(self):
        avg = round(self.average(self._recentPrices), 5)
        self._previousRecentPrices = self._recentPrices
        self._recentPrices = []
        self.updatePrice(avg)

    def updatePrice(self, price):
        self.currentPrice = float(price)
        self.recentPrices.append(self.currentPrice)
        recentPricesSorted = sorted(self.recentPrices)

        if (self.highPrice == 0 or self.lowPrice == 0):
            self.resetData("_buyTrigger 0's")
            return

        if (self.currentPrice > self.highPrice ):
            #Price is higher than highest price
            self.steadyCount = 0
            self.lastUpdated = 1
            self.highPriceCounter = self.highPriceCounter + 1
            self.lowPriceCounter = 0
        elif (self.currentPrice < self.lowPrice ):
            #Price is lower than lowest price
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

        #sell on stock going down % from high
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
            self.app_log.info(str(self.currentPrice), str(self.purchasePrice))
            self.resetData("_sellTrigger P/L Profit. Set at: " + str(Settings.config.getfloat("sellSettings", "percentGained", fallback=5 )))
        
        #sell on stock staying steady
        elif (self.steadyCount >= Settings.config.getfloat("sellSettings", "steadyCount", fallback=20 )):
            self.triggered = False
            self.resetData("_sellTrigger Steady Count")

        #sell if stock changes low price X times
        elif (self.lowPriceCounter >= Settings.config.getfloat("sellSettings", "lowPriceChanges", fallback=3 )):
            self.triggered = False
            self.resetData("_sellTrigger Low price changes")

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
        self.steadyCount = 0.0

    def shouldIPurchase(self):
        if (self.isTriggered()):
            self.printStockData()
            print("Should Buy Now")
            return True
        return False

    def shouldISell(self):
        if (self.isTriggered() == False):
            print("Should Sell Now")
            return True
        else:
            return False

    def isTriggered(self):
        return self.triggered

    def isValid(self):
        if (self.symbol != "" and self.isValidExchange()):
            return True
        return False
            
    def isValidExchange(self):
        if (self.exchange.upper() in Settings.config.get("default", "validExchanges" )):
            return True
        return False