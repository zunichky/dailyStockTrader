class LiveStockData:

    def __init__(self, json, ticker = "",  quote=False):
        self._reset()
        if (quote == True):
            self._parseJsonQuote(ticker, json)
        else:
            self._parseJson(json)
    
    def _parseJson(self, data):
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
            self.currentPrice = data[ticker]["bidPrice"]
            self.exchange = str(data[ticker]["exchangeName"]).upper()
            self.valid = True
        except:
            try:
                self.symbol = data[ticker.lower()]['symbol'].upper()
                self.currentPrice = data[ticker.lower()]["bidprice"]
                self.exchange = str(data[ticker.lower()]["exchangename"]).upper()
                self.valid = True
            except:
                print("Can't parse json quote")
                print(data)
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
    
    def isValidExchange(self):
        if (self.exchange == "NASD" or self.exchange == "NYSE" or self.exchange == "AMEX"):
            return True
        return False
