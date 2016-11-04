import datetime
import json
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("Strategy Simulator")
logger.setLevel(logging.INFO)
ch=logging.StreamHandler()
ch.setLevel(logging.INFO)
logger.addHandler(ch)

class Instrument(object):
    """
    Instrument is a stock or future, it associates with itself
    data such as prices and update time
    """
    def __init__(self, id, name, sym, itype="stock"):
        if itype not in ["future","stock"]:
            raise ValueError("Type of Instrument is not supported : {}".format(itype))
        if type(id) != int:
            raise ValueError ("Your instrument id is invalid {}".format(id))
        self.type = itype
        self.id = id
        self.current_raw = {}
        self.data={}
        self.symbol=sym
        self.name=name
        self.ts=None
        self.prices = pd.Series()
        self.holdings=0
        return

    def update(self,ts, price):
        self.data["price"]=price
        self.ts=pd.Timestamp(ts)
        self.prices = self.prices.append(pd.Series(self.price, [self.ts]))
        return

    @property
    def price(self):
        return self.data.get("price",float('nan'))

    def __unicode__(self):
        return u"[I][{type},{id}][{sym}] {name}: {price} @ {time}, {low}~{high}".format(type=self.type,
                id=self.id, sym=self.symbol, price=self.price, name=self.name,
                time=self.ts, low=self.data.get("lowPrice",float('nan')),high=self.data.get("highPrice",float('nan')))

    def __str__(self):
        return self.__unicode__().encode("utf-8")


class Subroutine(object):
    """
    Subroutines are modular algorithms that have
    internal states and iteract with the main alglrithm
    through input of prices/time and output of decisions
    init -> update (price/time) * N ->  output (terminate, buy/sell)
    importantly, a subroutine traces one instrument
    """
    def __init__(self, inst, unit,**kwargs):
        self.inst=inst
        self.unit=unit
        self.init(**kwargs)

    def init(self,**kwargs):
        for k, v in kwargs.items():
            setattr(self,k,v)
        return

    def update(self, instUpdate=False):
        pass

    def output(self):
        """
        none -> terminated
        positive amount -> buy
        negative amount -> sell
        """
        return None

class ThresholdControl(Subroutine):
    """
    This subroutine aims to reduce risk by moving towards neutral units holding
    influenced by the gain at present
    """
    def __init__(self, inst, fund, unit, winningPer=0.4, losingPer=0.2,
            sellingPerWin=0.5, sellingPerLose=0.4, **kwargs):
        self.inst=inst
        self.prices=[self.inst.price]
        self.funds=[fund]
        self.units=[unit]
        self.total0=fund+unit*self.inst.price
        self.times=[self.inst.ts]
        self.winningPer=float(winningPer)
        if self.winningPer>1:
            raise ValueError("Winning Per incorrect")
        self.losingPer=float(losingPer)
        if self.losingPer>1:
            raise ValueError("Losing Per incorrect")
        self.sellingPerWin=float(sellingPerWin)
        self.sellingPerLose=float(sellingPerLose)
        if self.sellingPerWin>1 or self.sellingPerLose>1:
            raise ValueError("Selling Per incorrect")

    def update(self, fundIn, deltaUnit=0):
        self.prices.append(self.inst.price)
        self.times.append(self.inst.ts)
        fund=fundIn
        unit=self.units[-1]+deltaUnit
        if unit==0:
            return 0
        total=fund+unit*self.prices[-1]
        gain=total-self.total0
        # logger.info("Current gain {}, total {} fund {} unit {}".format(gain,total, fund, unit))
        if gain>=0 and gain/self.total0>=self.winningPer:
            sellingUnit = abs(gain)*self.sellingPerWin/self.inst.price
            if sellingUnit>=abs(unit):
                sellingUnit=abs(unit)
            if unit>=0:
                sellingUnit=-sellingUnit
            else:
                pass
            logger.info("Winning Control: gain={}({}), selling {} units".format(gain, gain/self.total0, sellingUnit ))
            self.units.append(unit+sellingUnit)
            self.funds.append(fund+sellingUnit*self.inst.price)
            return sellingUnit
        elif gain<=0 and abs(gain/self.total0)>=self.losingPer:
            sellingUnit = abs(gain)*self.sellingPerLose/self.inst.price
            if sellingUnit>=abs(unit):
                sellingUnit=abs(unit)
            if unit>=0:
                sellingUnit=-sellingUnit
            else:
                pass
            logger.info("Losing Control: gain={}({}), selling {} units".format(gain, gain/self.total0, sellingUnit))
            self.units.append(unit+sellingUnit)
            self.funds.append(fund+sellingUnit*self.inst.price)
            return sellingUnit
        else:
            self.funds.append(fund)
            self.units.append(unit)
        return 0

class Chasing(Subroutine):
    """
    This strategy aims to chase the larger scale trend of the instrument
    in growing trend the goal is to maximize gain with risk management
    in shrinking trend the goal is to increase holdings with risk management
    """
    def __init__(self, inst, unit, direction=1, priceGap=3.0,
            buyInit=0.7, buyDelta=0.1, buyRetain=0.8, buyRetainDelta=0.2,
            sellInit=0.8, sellDelta=0.1, sellRetain=0.6, sellRetainDelta=0.2, **kwargs):
        self.inst=inst
        self.prices=[self.inst.price]
        self.times=[self.inst.ts]
        self.direction=direction
        self.directions=[self.direction]
        self.units=[unit]
        self.priceGap=priceGap
        self.buyInit=buyInit
        self.buyDelta=buyDelta
        self.buyRetain=buyRetain
        self.buyRetainDelta=buyRetainDelta
        self.sellInit=sellInit
        self.sellDelta=sellDelta
        self.sellRetain=sellRetain
        self.sellRetainDelta=sellRetainDelta
    def update(self):
        price0=self.prices[-1]
        price=self.inst.price
        time=self.inst.ts
        unit0=0
        if abs(price-price0)<self.priceGap:
            return 0
        total=0
        for p, u in zip(self.prices,self.units):
            total+=p*u
            unit0+=u
        gains=unit0*price-total
        self.prices.append(price)
        self.times.append(time)
        if price-price0>=0:
            direction=1
        else:
            direction=-1
        self.directions.append(direction)
        if direction>0 and self.direction>0:
            self.direction+=direction
        elif direction<0 and self.direction<0:
            self.direction+=direction
        else:
            self.direction=direction
        if direction>=0:
            selling=self.sellInit-(self.direction-1)*self.sellDelta
            if selling<0: selling=0
            sellingUnit=gains*selling/price
            netgain=selling*gains
            buying=self.sellRetain-(self.direction-1)*self.sellRetainDelta
            if buying<=0: buying=0
            buyingUnit=netgain*buying/price
            netUnit=sellingUnit-buyingUnit
            self.units.append(netUnit)
            return -netUnit
        elif direction<0:
            buying=self.buyInit-(-self.direction-1)*self.buyDelta
            if buying<=0: buying=0
            buyingUnit=gains*buying/price
            netgain=buying*gains
            selling=self.buyRetain-(-self.direction-1)*self.buyRetainDelta
            if selling<0: selling=0
            sellingUnit=netgain*selling/price
            netUnit=buyingUnit-sellingUnit
            self.units.append(netUnit)
            return -netUnit


class TurningPoint(Subroutine):
    """
    This strategy aims to micromanage small scale fluctuations
    the goal can be to increase fund, increase or decrease holdings,
    or to increase hand size
    """

    def __init__(self, inst, mode="increase", n=10,
            n_delta=1, h=1.0, **kwargs):
        self.inst=inst
        self.pt=self.inst.price
        self.mode=mode
        self.prices=[self.pt]
        self.times=[self.inst.ts]
        self.highs=[]
        self.n_delta=n_delta
        self.h=h
        self.lows=[]
        self.gain=0
        if mode not in ["increase", "decrease", "size"]:
            raise ValueError("Mode error")
        self.selling=n
        self.buying=n
        self.cnt=0
        self.direction=0
        self.high=-10000
        self.low=10000
        return

    def update(self):
        price0=self.prices[-1]
        price=self.inst.price
        self.prices.append(price)
        self.times.append(self.inst.ts)
        if price > price0:
            direction=1
        elif price < price0:
            direction=-1
        else:
            return 0
        if self.direction==0:
            self.direction=direction
            return 0
        if self.direction>0 and direction<0:
            self.high=price0
            self.highs.append(self.high)
        elif self.direction<0 and direction>0:
            self.low=price0
            self.lows.append(self.low)
        self.direction=direction
        if direction==1 and price-self.low >= self.h:
            self.gain-=self.buying*price
            return self.buying
        elif direction==-1 and self.high - price >= self.h:
            self.gain+= self.selling*price
            if self.gain>0:
                self.cnt+=1
                if self.n_delta > self.gain/price:
                    self.n_delta=self.gain/price
                if self.n_delta<1:
                    self.n_delta=0
                if self.mode=="increase":
                    self.buying+=self.n_delta
                elif self.mode=="decrease":
                    self.selling+=self.n_delta
                else:
                    self.buying+=self.n_delta
                    self.selling+=self.n_delta
            return -self.selling
        return 0



class PrototypeStrategyI(object):
    """
    This is a prototype strategy that centers around 3 subroutines:
    1, threshold management
    2, (low resolution) decremental chasing
    3, (high resolution) turning point strategy
    """
    def __init__(self, inst, fund, unit, unitInit, **kwargs):
        self.inst=inst
        self.fund=fund
        self.unit=unit
        self.total0=fund+unit*self.inst.price
        self.unitInit=unitInit
        self.ts=[]
        self.funds=[]
        self.units=[]
        self.gains=[]
        self.orders=[]
        self.prices=[]
        self.kwargs={}
        for k,v in kwargs.items():
            try:
                self.kwargs[k]=float(v)
            except:
                pass
        self.ThresholdControlRoutine=ThresholdControl(inst, fund, unit, **self.kwargs)
        self.ChasingRoutine=Chasing(inst, unitInit, **self.kwargs)
        self.TurningPointRoutine=TurningPoint(inst, **self.kwargs)
    def transact (self,n,src="other"):
        """
        negative n=> selling
        """
        if self.fund - self.inst.price*n <= 0:
            logger.warn("Running out of funds when trying to transact {}".format(n))
            newn=self.fund/self.inst.price
            self.unit+=newn
            self.fund=0
        else:
            self.fund-=self.inst.price*n
            self.unit+=n
        self.orders.append((self.inst.ts, self.inst.price, n, src))
    def update(self):
        # logger.info("Current: fund {}, unit {}, price {}".format(self.fund, self.unit, self.inst.price))
        self.ts.append(self.inst.ts)
        self.prices.append(self.inst.price)
        self.funds.append(self.fund)
        self.units.append(self.unit)
        self.gains.append(self.fund+self.unit*self.inst.price-self.total0)
        n= self.ChasingRoutine.update()
        n2=self.ThresholdControlRoutine.update(self.fund, n)

        def breach(n2, src="Chasing"):
            logger.info("Threshold breached from {}! Transacting {}".format(src, n2))
            self.transact(n2,"threshold")
            if self.unit>0:
                logger.info("Restarting a Chasing Routine with {}".format(self.unit))
                self.ChasingRoutine=Chasing(self.inst, self.unit, **self.kwargs)
            elif self.unit<=0:
                self.transact(-self.unit+self.unitInit,"reset")
                logger.info("Restarting a Chasing Routine with {}".format(self.unit))
                self.ChasingRoutine=Chasing(self.inst, self.unit, **self.kwargs)
            logger.info("Restarting a Turning Point Routine")
            self.TurningPointRoutine=TurningPoint(self.inst, **self.kwargs)

        if n2!=0:
            breach(n2)
        else:
            if n!=0:
                logger.info("Chasing updated! Transacting {}".format(n))
                self.transact(n,src="chasing")
                logger.info("Restarting a Turning Point Routine")
                self.TurningPointRoutine=TurningPoint(self.inst, **self.kwargs)
            else:
                n=self.TurningPointRoutine.update()
                n2=self.ThresholdControlRoutine.update(self.fund, n)
                if n2==0:
                    # logger.info("Turning point updated! Transacting {}".format(n))
                    self.transact(n,src="turningpoint")
                else:
                    breach(n2, "Turing Point")
        return
