from logging import NullHandler
from config import Settings
from tda import auth
from dbConnection import *
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
        if (Settings.config.getboolean("default", "pullFromDB") == False):
            cls._token_path = Settings.config.get("tdAccountSettings", "tokenPath" )
            cls._api_key = Settings.config.get("tdAccountSettings", "apiKey" )
            cls._redirect_uri = Settings.config.get("tdAccountSettings", "redirectUri" )
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
            if (PostgreSQL.isInitialized == False):
                PostgreSQL.isInitialized.setup()
            
            #strftime("%Y-%m-%d %H:%M:%S")'
            time2 = time.strftime("%Y-%m-%d %H:%M:%S")
            time1 = (time - datetime.timedelta(milliseconds= 2500)).strftime("%Y-%m-%d %H:%M:%S")
            selectQuery = "SELECT rawjson, key FROM public.rawstockdata WHERE timestamp BETWEEN '{}' AND '{}'".format(time1, time2)
            data = PostgreSQL.select(selectQuery)
            if (len(data) > 0):
                x = json.dumps(data[-1][0])
                y = json.loads(x)
                return y

            return ""
        else:
            returnData = ""
            try:
                returnData = cls._c.get_quotes(Settings.getWatchStocks()).json()
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
