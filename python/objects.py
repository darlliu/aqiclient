from __future__ import unicode_literals
import datetime
import urllib,urllib2
import httplib
import json
import sys
import pandas as pd
import numpy as np
import logging
logger = logging.getLogger("REST Client")
logger.setLevel(logging.INFO)
ch=logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)
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
            logger.debug("Connected")
            return res.read()
        else:
            logger.warning("ERR: {}".format(res.status))
            return None
    def action(conn, url, action="GET",params=""):
        params = json.dumps(params)
        if action not in ["POST","GET","PUT"]:
            raise ValueError("Cannot perform this action: {}".format(action))
        def inner():
            if action == "POST":
                req = conn.h.request(action, url, params, conn.headers)
            elif action == "GET":
                req = conn.h.request(action, url)
            else:
                raise NotImplemented("This method is not supported yet")
            res = conn.h.getresponse()
            return res
        try:
            res= inner()
        except:
            logger.debug("Trying to refresh")
            conn.refresh()
            res = inner()
        if res.status == 200:
            return res.read()
        else:
            logger.info("ERR:{} {}".format(res.status, res.reason))
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
            logger.info( "INSTRUMENT: UPDATE FAILED {}".format(res))
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
            logger.info("No account found")
            return 0
        return 0

    @property
    def price(self):
        return self.data.get("price",float('nan'))

    def __unicode__(self):
        return u"[I][{type},{id}][{sym}] {name}: {price} @ {time}, {low}~{high}".format(type=self.type,
                id=self.id, sym=self.symbol, price=self.price, name=self.name,
                time=self.ts, low=self.data.get("lowPrice",float('nan')),high=self.data.get("highPrice",float('nan')))

    def __str__(self):
        return self.__unicode__().encode("utf-8")

    def orderSell(self, units):
        pass

    def orderBuy(self, units):
        pass

class SimulatedInstrument(Instrument):

    def __init__(self,name, sym,itype=None, acct=None):
        super(SimulatedInstrument,self).__init__(-1,itype,acct)
        self.name=name
        self.symbol=sym

    def update(self,ts, price):
        self.data["price"]=price
        self.ts=pd.Timestamp(ts)
        self.prices = self.prices.append(pd.Series(self.price, [self.ts]))
        return

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
    Accounts are associated with one portfolio
    """
    def __init__(self, id, port, itype="cash", **kwargs):
        self.id=id
        self.port=port
        self.itype=itype
        self.v={}
        for key, val in kwargs.items():
            self.v[key]=val
        self.name=self.v.get("name","Account")
    @property
    def cash(self):
        return float(self.v.get("cashQty","0"))

    def __unicode__(self):
        return u"[A][{id}][type:{type}][broker:{broker}] {name}: {cash}".format(type=self.itype,
                id=self.id, broker=self.v.get("brokerID","NA"), name=self.name, cash=self.cash)

    def __str__(self):
        return self.__unicode__().encode("utf-8")

    def verify(self):
        """verify the account by id"""
        res=CONN.action("/api/user/accounts/verify?id={}".format(self.id))
        if res is None:
            return False
        else:
            return True


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
        #insert get account code here
        res=CONN.action("/api/user/accounts")
        res=json.loads(res)
        for v in res:
            if int(v["portfolioID"])==self.id:
                self.accounts[v["accountID"]]=Account(v["accountID"],self, v["accountType"], **v)
        #insert get instrument code here
        self.pools={}
        self.ts=None
        self.data={}
        return

    def update(self):
        """
        Obtains updated information for the portfolio
        """
        res = CONN.action("/api/portfolio?portfolioID={}".format(self.id))
        if not res:
            logger.info("PORTFOLIO: UPDATE FAILED {}".format(res))
        self.current_raw=json.loads(res).get(str(self.id),{})
        self.name=self.current_raw.get("name",None)
        self.active=self.current_raw.get("active","false")
        self.createDate=self.current_raw.get("createDate","")
        for k in ["value","stopLoss","stopWin","initialValue","pnl","gain","change","changePercentage","sharpeRatio","mDD","iRR","risk","beta"]:
            self.data[k]=float(self.current_raw.get(k,"nan"))
        self.ts=pd.Timestamp(datetime.datetime.now())
        return


    def __unicode__(self):
        return u"[P][{id}][active:{active}][{date}] {name}: {price} @ {time}, {low}~{high}".format(type=self.type,
                id=self.id, active=self.active, name=self.name, date=self.createDate, price=self.data.get("value",float("nan")),
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
    def __init__(self,**kwargs):
        self.cleared=False
        self.terminated=False
        self.createDate=pd.Timestamp(datetime.datetime.now())
        self.status="unknown"
        return
    def update(self, id=None):
        """
        get an order detail from the api
        """
        if id:
            self.id=id
        if not hasattr(self,"id"):
            return
        res = CONN.action("/api/orders?orderID={}".format(self.id))
        self.current_raw=json.loads(res)[0]
        self.createDate=pd.Timestamp(self.current_raw["createDate"])
        self.accountID=int(self.current_raw["accountID"])
        self.portID=int(self.current_raw["portfolioID"])
        self.instID=int(self.current_raw["instrumentID"])
        self.direction=self.current_raw["direction"]
        self.price=float(self.current_raw["price"])
        self.qty=float(self.current_raw["qty"])
        self.status=self.current_raw["status"]
        return
    def place(self, account, port, inst, direction, price, qty, expr=None):
        """
        Place an order to the api
        """
        if direction not in ["long","short"]:
            raise ValueError("Direction not supported: {}".format(direction))
        self.accountID=account.id
        self.portID=port.id
        self.instID=inst.id
        self.direction=direction
        self.price=price
        self.qty=qty
        if expr:
            self.expr=expr
        args = {"accountID":self.accountID, "instrumentID":self.instID,
                "portfolioID":self.portID, "type":self.direction,
                "price":self.price, "qty":self.qty}
        print args
        res=CONN.action("/api/orders", action="POST", params=args)
        if res:
            logger.info("POST order complete: {}".format(str(self)))
        print res
        return
    def verify(self):
        """
        verify an order
        """
        self.update()
        return self.status

    def __unicode__(self):
        return u"[O][{id}][inst:{inst}][portfolio:{port}, account:{acct}][{direction}] {status}: {price} @ {qty}".format(
                id=self.id,acct=self.accountID, inst=self.instID, port=self.portID, price=self.price,
                qty=self.qty, direction=self.direction, status=self.status)

    def __str__(self):
        return self.__unicode__().encode("utf-8")

class Strategy(object):
    """
    A strategy takes in a portfolio and manipulates it according to some internal login
    and external information
    """

    def __init__(self,name, portfolio):
        self.name = name
        self.pro = portfolio
        return

    def init(self,**kwargs):
        """
        A method to initialize the strategy
        """
        return

    def update(self, **kwargs):
        """
        A method to iterate through the strategy
        A strategy can hold/wait, do nothing or perform some operations based on
        some internal states
        """
        return


class ThresholdTurningPointSubroutine(object):
    def __init__(self, sid, opt,pt, h, t, direction=1):
        self.sid=sid
        self.t=t
        self.tend=t
        self.pt=pt
        self.opt=opt
        self.pend=pt
        self.h=h
        self.direction=direction
        self.terminated=False
        self.cleared=False
        logger.debug("created subroutine {} at direction {}, price is {}".format(self.sid, direction,self.opt))

    def update(self,p,t):
        if self.direction==-1 and p < self.pt:
            logger.debug("""if shorting and price dropped too low""")
            self.tend=t
            self.pend=p
            self.terminated=True
            return
        elif self.direction==1 and p>self.pt:
            logger.debug("""longing and price too high""")
            self.tend=t
            self.pend=p
            self.terminated=True
            return
        if self.direction==-1:
            if self.opt-p>=self.h:
                logger.debug("Subroutine (sell) {} cleared at price {}, delta {}, margin {}".format(self.sid, p,self.opt-p, p-self.pt))
                self.tend=t
                self.pend=p
                self.cleared=True
                return
        else:
            if p-self.opt >=self.h:
                self.tend=t
                self.pend=p
                logger.debug("Subroutine (buy) {} cleared at price {}, delta {}, margin {}".format(self.sid, p,self.opt-p, p-self.pt))
                self.cleared=True
                return
        return


class ThresholdTurningPoint(Strategy):
    """
    A test
    """
    def __init__(self,name, portfolio, inst, funds, simulated=False):
        super(ThresholdTurningPoint,self).__init__(name, portfolio)
        self.sim=simulated
        self.params={}
        self.inst=inst
        self.min=None
        self.max=None
        self.funds=funds
        self.ofunds=funds
        self.units=0
        self.ts=[]
        self.ps=[]
        self.orders={}
        self.routines=[]

    def init(self,n,h, units, nmode="fixed",hmode="abs",**kwargs):
        self.stacks=[]
        self.pt=self.inst.price
        if self.pt*units > self.funds:
            logger.warn("Not enough funds, buying all!")
            units=int(self.funds/self.pt)
        self.funds -= units*self.pt
        self.funds_series=[]
        self.units = units
        self.units_series=[]
        self.gains_series=[]
        self.n=n
        self.h=h
        self.hmode=hmode
        self.nmode=nmode
        self.cnt=0
        self.direction=0
        for key, val in kwargs.items():
            self.params[key]=val
        return

    def placeUnits(self, u,p,thr1=0, thr2=0, direction=1):
        logger.debug("Placing unit {}@price {} with funds {}".format(u,p,self.funds))
        if direction==-1: #long
            if (self.units - u)*p+self.funds<thr1:
                logger.warning("Running out of funds!")
                return False
            else:
                self.units -= u
                self.funds+=u*p
                return True
        else:
            if self.funds-u*p < thr2:
                logger.warning("Running out of funds!")
                return False
            else:
                self.units += u
                self.funds -= u*p
                return True
        return False

    def update(self,**kwargs):
        def clearStacks(stacks):
            for s2 in self.stacks:
                s2.update(p_cur,self.inst.ts)
                if s2.cleared:
                    n=self.n #may change
                    if self.placeUnits(n,p_cur,direction=s2.direction):
                        if s2.direction==-1:
                            self.inst.orderSell(n)
                        else:
                            self.inst.orderBuy(n)
                        self.orders[s2.sid]=(s2.direction, s2.t, s2.opt, self.inst.ts, p_cur)
                        # self.pt=p_cur
                    else:
                        logger.info("Failed to place order for {} at price {} for unit {}".format(s2.sid, p_cur, n))
                elif s2.terminated:
                    logger.debug("{} terminated at price {}".format(s2.sid, p_cur))
                else:
                    stacks.append(s2)
            return stacks
        stacks = []
        p_old=self.inst.price
        self.ts.append(self.inst.ts)
        self.ps.append(self.inst.price)
        if self.sim:
            t=kwargs.get("t")
            p=kwargs.get("p")
            self.inst.update(t,p)
        else:
            self.inst.update()
        p_cur=self.inst.price
        if p_cur==p_old:
            logger.debug("No change...")
            return
        stacks=clearStacks(stacks)
        if p_cur>p_old:
            direction = 1
        else:
            direction = -1
        if self.direction != direction:
            self.direction=direction
            if p_cur>p_old:
                s = ThresholdTurningPointSubroutine(self.cnt, p_old, self.pt, self.h,self.inst.ts, 1)
            else:
                s = ThresholdTurningPointSubroutine(self.cnt, p_old, self.pt, self.h,self.inst.ts, -1)
            self.routines.append(s)
            s.update(p_cur,self.inst.ts)
            stacks.append(s)
        self.stacks =stacks
        self.funds_series.append(self.funds)
        self.units_series.append(self.units)
        self.gains_series.append(self.funds+self.units*p-self.ofunds)
        self.cnt+=1
        return
    def clearOrders(self,**kwargs):
        #need to clear order and recalculate unit/funds here
        return

if __name__ == "__main__":

    # print CONN.action("/api/user/accounts")
    # print CONN.action("/api/user/accounts/verify?id=1")
    # print CONN.action("/api/orders")
    print CONN.action("/api/instruments/historical-data?interval=minute&symbols=au1406")
    # print CONN.action("/api/orders")
    # print CONN.action("/api/portfolio?portfolioID=3")
    # print CONN.action("/api/portfolio?portfolioID=23")
    # print CONN.action("/api/portfolio?portfolioID=63")
    # print CONN.action("/api/portfolio?portfolioID=3")
    PORT=Portfolio(id=23,itype="stock")
    PORT.update()

    print PORT
    INST=SimulatedInstrument("Apple","APPL","stock")
    for inst in GetAllInstruments(None):
        inst.update()
        print inst
        inst.update()
        print inst.prices
        if inst.id>10:
            break
    ACCT=PORT.accounts.values()[0]
    print ACCT

    ORDER=Order()
    ORDER.update(id=89)
    print ORDER
    ORDER.place(ACCT,PORT, inst, "long", 10, 1)
    ORDER.update()
    print ORDER
    print CONN.action("/api/orders",action="POST", params={
        "instrumentID":88,"portfolioID":17, "accountID":1 ,"qty":-1, "type":"short",
        "price":4000})
