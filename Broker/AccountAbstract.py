from abc import ABC, abstractmethod

class Account(ABC):
    settings = ""

    def __init__(self, settings):
        self.currentHoldings = []
        self.balance = 0
        self.pl = 0.0
        self.settings = settings

    @abstractmethod
    def purchaseStock(self, ticker, limitPrice = 0):
        pass

    @abstractmethod
    def sellStock(self, ticker, limitPrice = 0):
        pass
    
    @abstractmethod
    def getAccountBalance(self):
        pass
  
class Broker(ABC):
    @abstractmethod
    def __init__(self):
        pass
    
    @abstractmethod
    def getQuotes(self, tickerList, time = ""):
        pass