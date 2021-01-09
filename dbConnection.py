
import psycopg2
import json
import config

class PostgreSQL(object):
    _connection = ""
    _user = ""
    _password = ""
    _dataBase = ""
    _cursor = ""
    _valid = False

    @classmethod
    def setup( cls , user = "", password = "", dbName = ""):
        if (user == ""):
            cls._user = config.Settings.config.get("dbSettings", "user" )
        else:
            cls._user = user

        if (password == ""):
            cls._password = config.Settings.config.get("dbSettings", "password" )
        else:
            cls._password = password
        
        if (dbName == ""):
            cls._dataBase = config.Settings.config.get("dbSettings", "dbName" )
        else:
            cls._dataBase = dbName

        cls._valid = True

    @classmethod
    def insert(cls, insertStatement ):
        success = False
        try:
            cls._open()
            cls._cursor = cls._connection.cursor()
            cls._cursor.execute(insertStatement)
            cls._connection.commit()
            success = True
        except:
            success = False
            print("failed to write to db")
        finally:
            cls._close()
        return success
    
    @classmethod
    def select(cls, statememt):
        cls._open()
        cls._cursor = cls._connection.cursor()
        cls._cursor.execute(statememt)
        returnData =  cls._cursor.fetchall()
        cls._close()
        return returnData
        '''
        SELECT key, rawjson
	FROM public.rawstockdata
	WHERE timestamp BETWEEN '2021-01-7 22:21:00'::timestamp
                 AND now()::timestamp;
    '''

    @classmethod
    def isInitialized(cls):
        return cls._valid

    @classmethod
    def _open(cls):
        try:
            # Connect to an existing database
            cls._connection = psycopg2.connect(user=cls._user,
                                        password=cls._password,
                                        host="localhost",
                                        port="5433",
                                        database=cls._dataBase)

        except (Exception) as error:
            print("Error while connecting to PostgreSQL", error)

    @classmethod
    def _close(cls):
        if (cls._connection):
            cls._cursor.close()
            cls._connection.close()