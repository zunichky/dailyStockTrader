
from logging import NullHandler
from .AccountAbstract import *
from tda import auth, client

class TdAccount(Account): 
    def __init__(self, settings):
        super().__init__(settings)

    def authorize(self, test):
        print("Real Authorized")

    def purchaseStock(self, ticker, limitPrice = 0):
        print("Purchase Real: " + ticker )

    def sellStock(self, ticker, limitPrice = 0):
        print("Sell Real: " + ticker)
    
    def doIOwnThisStock(self, ticker):
        for y in self.currentHoldings:
            if (y.symbol == ticker):
                return True
        return False

    def getAccountBalance(self):
        print("$100 Real")
    
    def currentHoldings(self):
        print("No Real Holdings")

class TdBroker(Broker):
    _c = ""
    _token_path = ""
    _api_key = ""
    _redirect_uri = NullHandler
    account = ""

    def __init__(self,  tokenPath, apiKey, redirectUri):   
        self._token_path = tokenPath
        self._api_key = apiKey
        self._redirect_uri = redirectUri
        
        try:
            self._c = auth.client_from_token_file(self._token_path, self._api_key)
        except FileNotFoundError:
            from selenium import webdriver
            with webdriver.Chrome() as driver:
                self._c = auth.client_from_login_flow(
                    driver, self._api_key, self._redirect_uri, self._token_path)
    
    def newAccount(self, accountNumber):
        self.account = TdAccount(accountNumber)

    def getQuotes( self , tickerList, time=""):
        returnData = ""
        try:
            returnData = self._c.get_quotes(tickerList).json()
        except:
            returnData = ""
        return returnData
    