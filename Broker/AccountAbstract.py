from abc import ABC, abstractmethod
import enum
class Account(ABC):
    settings = ""

    def __init__(self, settings):
        self.currentHoldings = []
        self.balance = 0
        self.cashBalance = 0
        self.availableFunds = 0
        self.buyingPower = 0
        self.dayTradingBuyingPower = 0
        self.equity = 0
        self.pl = 0.0
        self.currentOrders = []
        self.settings = settings
        self.sellPrice = 0
    '''
    @abstractmethod
    def purchaseStockMarket(self, ticker, price = 0):
        pass

    @abstractmethod
    def sellStock(self, ticker, price = 0):
        pass
    '''

class Order():
    status = ""
    orderId = 0
    targetPrice = 0
    quantity = 0
    quantityToBeFilled = 0

    @abstractmethod
    def __init__(self):
        pass

class Broker(ABC):
    @abstractmethod
    def __init__(self):
        pass
    
    @abstractmethod
    def getQuotes(self, tickerList, time = ""):
        pass

class results(enum.Enum):
    ACCEPTED = 'ACCEPTED'
    AWAITING_CONDITION = 'AWAITING_CONDITION'
    AWAITING_MANUAL_REVIEW = 'AWAITING_MANUAL_REVIEW'
    AWAITING_PARENT_ORDER = 'AWAITING_PARENT_ORDER'
    AWAITING_UR_OUR = 'AWAITING_UR_OUR'
    CANCELED = 'CANCELED'
    EXPIRED = 'EXPIRED'
    FILLED = 'FILLED'
    PENDING_ACTIVATION = 'PENDING_ACTIVATION'
    PENDING_CANCEL = 'PENDING_CANCEL'
    PENDING_REPLACE = 'PENDING_REPLACE'
    QUEUED = 'QUEUED'
    REJECTED = 'REJECTED'
    REPLACED = 'REPLACED'
    WORKING = 'WORKING'