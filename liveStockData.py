class LiveStockData:

    def __init__(self, json, ticker = "", fakeData=False):
        self._reset()
        if (fakeData == True):
            self._parseFakeJson(json)
        else:
            self._parseJsonQuote(ticker, json)
    
    def _parseFakeJson(self, data):
        try:
            self.symbol = data["content"][0]["key"]  
            self.currentPrice = str(data["content"][0]["LAST_PRICE"])
            self.exchange = str(data["content"][0]["EXCHANGE_NAME"])
            self.valid = True
        except:
            self._reset()

    def _parseJsonQuote(self, ticker, data):
        try:
            self.symbol = data[ticker]['symbol'].upper()
            self.currentPrice = data[ticker]["lastPrice"]
            self.exchange = str(data[ticker]["exchangeName"]).upper()
            self.valid = True
        except:
            try:
                self.symbol = data[ticker.lower()]['symbol'].upper()
                self.currentPrice = data[ticker.lower()]["lastprice"]
                self.exchange = str(data[ticker.lower()]["exchangename"]).upper()
                self.valid = True
            except:
                print("Can't parse json quote for: " + ticker)
                self._reset()
                return
        #check for empty ticker
        if (self.symbol == ""):
            self._reset()
    
    def _reset(self):
        self.symbol = ""
        self.currentPrice = 0
        self.valid = False
        self.exchange = ""
    
    def isValid(self):
        return self.valid
    
    def isValidExchange(self, validExchanges):
        if (self.exchange in validExchanges):
            return True
        return False
