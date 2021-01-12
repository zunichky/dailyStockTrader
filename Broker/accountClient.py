class AccountClient:
    
    def __init__(self):
        self.currentHoldings = []
        self.balance = 0
        self.pl = 0.0

    def purchaseStock(self, ticker):
        raise NotImplementedError("Don't forget to implement")
    
    def sellStock(self):
        raise NotImplementedError("Don't forget to implement")
    
    def getAccountBalance(self):
        raise NotImplementedError("Don't forget to implement")
    
    def holdingStock(self):
        raise NotImplementedError("Don't forget to implement")
