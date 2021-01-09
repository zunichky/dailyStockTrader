from logging import NullHandler
import config
from tda import auth, client
import config
import dbConnection
import datetime
import json

class Client(object):
    _updated = False
    _filePath = ""
    _stocksTickersToWatch = []
    _lastConfigUpdate = 0
    _token_path = ""
    _api_key = ""
    _redirect_uri = ""
    _c = NullHandler
    _pullFromDb = False

    @classmethod
    def authorize( cls ):
        if (config.Settings.config.getboolean("default", "pullFromDB") == False):
            cls._token_path = config.Settings.config.get("tdAccountSettings", "tokenPath" )
            cls._api_key = config.Settings.config.get("tdAccountSettings", "apiKey" )
            cls._redirect_uri = config.Settings.config.get("tdAccountSettings", "redirectUri" )
            try:
                cls._c = auth.client_from_token_file(cls._token_path, cls._api_key)
            except FileNotFoundError:
                from selenium import webdriver
                with webdriver.Chrome() as driver:
                    cls._c = auth.client_from_login_flow(
                        driver, cls._api_key, cls._redirect_uri, cls._token_path)
    
    @classmethod
    def getQuotes( cls , pullFromDb = False, time = ""):
        if (pullFromDb == True):
            if (dbConnection.PostgreSQL.isInitialized == False):
                dbConnection.PostgreSQL.isInitialized.setup()
            
            #strftime("%Y-%m-%d %H:%M:%S")'
            time2 = time.strftime("%Y-%m-%d %H:%M:%S")
            time1 = (time - datetime.timedelta(milliseconds= 4500)).strftime("%Y-%m-%d %H:%M:%S")
            selectQuery = "SELECT rawjson, key FROM public.rawstockdata WHERE timestamp BETWEEN '{}' AND '{}'".format(time1, time2)
            data = dbConnection.PostgreSQL.select(selectQuery)
            if (len(data) > 0):
                x = json.dumps(data[-1][0])
                y = json.loads(x)
                return y

            return ""
        else:
            returnData = ""
            try:
                returnData = cls._c.get_quotes(config.Settings.getWatchStocks()).json()
            except:
                returnData = ""
            return returnData

    @classmethod
    def getQuote (cls, stock):
        returnData = ""
        try:
            returnData = cls._c.get_quotes([stock]).json()
        except:
            returnData = ""
        return returnData