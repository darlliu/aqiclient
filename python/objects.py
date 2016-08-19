from __future__ import unicode_literals
import datetime
import urllib,urllib2
import httplib
import json
import pandas as pd
import numpy as np
class RESTConnection(object):
    def __init__ (self, usr="charles", pwd="123", host="54.245.103.8"):
        self.usr = usr
        self.pwd = pwd
        self.host=host

        self.params = json.dumps({"id":usr,"password":pwd})
        self.headers = {"Content-Type":"application/json"}
        self.refresh()
        return
    def refresh(self):
        self.h = httplib.HTTPConnection(self.host)
        req = self.h.request("POST","/api/login", self.params, self.headers)
        res = self.h.getresponse()
        if res.status == 200:
            print "Connected"
            return res.read()
        else:
            print "ERR: {}".format(res.status)
            return None
    def action(conn, url, action="GET",**kwargs):
        params = json.dumps(kwargs)
        if action not in ["POST","GET","PUT"]:
            raise ValueError("Cannot perform this action: {}".format(action))
        def inner():
            if action == "POST":
                req = conn.h.request(action, url, params, self.headers)
            elif action == "GET":
                req = conn.h.request(action, url)
            else:
                raise NotImplemented("This method is not supported yet")
            res = conn.h.getresponse()
            return res
        try:
            res= inner()
        except:
            print "Trying to refresh"
            conn.refresh()
            res = inner()
        if res.status == 200:
            return res.read()
        else:
            print "ERR:{} {}".format(res.status, res.reason)
            return None

CONN=RESTConnection()

class Instrument(object):
    """
    Instrument is a stock or future, it associates with itself
    data such as prices and operations such as inquire, set up order etc
    Instruments need to have owners to function, the ones that don't are non-tradable
    """
    def __init__(self, id, itype=None, acct=None):
        if itype not in ["future","stock"]:
            raise ValueError("Type of Instrument is not supported : {}".format(itype))
        if type(id) != int:
            raise ValueError ("Your instrument id is invalid {}".format(id))
        self.type = itype
        self.id = id
        self.acct = acct
        self.current_raw = {}
        self.data={}
        self.symbol=""
        self.name=""
        self.ts=None
        self.prices = pd.Series()
        self.holdings=0
        return

    def update(self):
        """
        Obtains updated information for the instrument
        """
        res = CONN.action("/api/instruments?id={}".format(self.id))
        if not res:
            print "INSTRUMENT: UPDATE FAILED {}".format(res)
        self.current_raw=json.loads(res)[0]
        self.symbol=self.current_raw.get("symbol",None)
        self.name=self.current_raw.get("name",None)
        itype=self.current_raw.get("instrumentType",None)
        if itype!=self.type:
            raise ValueError("Instrument type incorrect {}".format(itype))
        for k in ["price","openPrice","closePrice","highPrice","lowPrice","highLimit","lowLimit","volumn","bid","ask"]:
            self.data[k]=float(self.current_raw.get(k,"nan"))
        self.ts=pd.Timestamp(datetime.datetime.now())
        self.prices = self.prices.append(pd.Series(self.price, [self.ts]))
        return

    def updateHolding(self):
        if self.acct == None:
            print "No account found"
            return 0
        return 0

    @property
    def price(self):
        return self.data.get("price",float('nan'))

    def __unicode__(self):
        return u"[{type},{id}][{sym}] {name}: {price} @ {time}, {low}~{high}".format(type=self.type,
                id=self.id, sym=self.symbol, price=self.price, name=self.name,
                time=self.ts, low=self.data.get("lowPrice",float('nan')),high=self.data.get("highPrice",float('nan')))

    def __str__(self):
        return self.__unicode__().encode("utf-8")

    def orderShort(self, units):
        pass

    def orderLong(self, units):
        pass

def GetAllInstruments(acct=None):
    res= CONN.action("/api/instruments")
    res = json.loads(res)
    res = sorted(res,key=lambda x: int(x["instrumentID"]))
    for inv in res:
        yield Instrument(int(inv.get("instrumentID",None)),inv.get("instrumentType",None),acct)

class Account(object):
    """
    Account objects that are used for actual trading.
    Instruments that have associated accounts can be traded
    Accounts have built in constraints on transactions
    """
    pass

class Portfolio(object):
    """
    Portfolio is a profile that exists on the serve side, and is associated with instruments
    It contains pools of instruments with varying units
    """
    def __init__(self, id, itype=None):
        if itype not in ["future","stock"]:
            raise ValueError("Type of Instrument is not supported : {}".format(itype))
        if type(id) != int:
            raise ValueError ("Your instrument id is invalid {}".format(id))
        self.type = itype
        self.id = id
        self.accounts = {}
        self.instruments = {}
        self.pools={}
        self.ts=None
        self.data={}
        return

    def update(self):
        """
        Obtains updated information for the portfolio
        """
        res = CONN.action("/api/portfolio?id={}".format(self.id))
        if not res:
            print "PORTFOLIO: UPDATE FAILED {}".format(res)
        self.current_raw=json.loads(res)[0]
        self.name=self.current_raw.get("name",None)
        self.active=self.current_raw.get("active","false")
        self.createDate=self.current_raw.get("createDate","")
        for k in ["value","stopLoss","stopWin","initialValue","pnl","gain","change","changePercentage","sharpeRatio","mDD","iRR","risk","beta"]:
            self.data[k]=float(self.current_raw.get(k,"nan"))
        self.ts=pd.Timestamp(datetime.datetime.now())
        return


    def __unicode__(self):
        return u"[{id}][active:{active}][{date}] {name}: {price} @ {time}, {low}~{high}".format(type=self.type,
                id=self.id, active=self.active, name=self.name, date=self.createDate, price=self.data.get("value",float("nan"))
                time=self.ts, low=self.data.get("stopLoss",float('nan')),high=self.data.get("stopWin",float('nan')))

    def __str__(self):
        return self.__unicode__().encode("utf-8")


class Unit(Portfolio):
    """
    A unit is a portion of a portfolio, used to diversity strategies
    """
    pass

class Order(object):
    """
    An order is placed by an instrument to long or short it
    """
    pass

class Strategy(object):
    """
    A strategy takes in a portfolio and manipulates it according to some internal login
    and external information
    """
    pass

if __name__ == "__main__":

    print CONN.action("/api/user")
    print CONN.action("/api/portfolio?portfolioID=3")
    print CONN.action("/api/portfolio/position?portfolioID=3")
    for inst in GetAllInstruments(None):
        inst.update()
        print inst
        inst.update()
        print inst.prices
        if inst.id>10:
            break
