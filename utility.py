
def getDifferencePercentage( purchasePrice, currentPrice):
    if (purchasePrice == currentPrice):
        return 0
    try:
        return  ((currentPrice - float(purchasePrice)) / currentPrice) * 100.0
    except ZeroDivisionError:
        return 0