import configparser
import json
import os

class Settings(object):
    _updated = False
    _filePath = ""
    config = configparser.ConfigParser()
    _stocksTickersToWatch = []
    _lastConfigUpdate = 0

    @classmethod
    def load( cls, filePath):
        cls._filePath = filePath
        os.path.getmtime(cls._filePath)
        cls.config.read(cls._filePath )
        cls._updated = True

    @classmethod
    def getWatchStocks( cls ):
        cls._updated = False
        #TODO try/catch "failed delimiter"
        tmpStocks = json.loads(cls.config.get("default","stocksToWatch").upper())
        cls._stocksTickersToWatch = list(set(tmpStocks))
        return cls._stocksTickersToWatch
    
    @classmethod
    def isConfigModified( cls ):
        if (os.path.getmtime(cls._filePath) != cls._lastConfigUpdate):
            cls.load(cls._filePath)
            cls._lastConfigUpdate = os.path.getmtime(cls._filePath)
    
    @classmethod
    def isUpdated( cls ):
        cls.isConfigModified()
        return cls._updated