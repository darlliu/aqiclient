#Simulation routines for testing the algorithms
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.style.use('ggplot')
import os
import time
import pandas as pd
from objects import *

def ThresholdTurningPointSimulatorApple(funds=100000,n=10,h=1,u=400, start_year=2014, end_year=2016):

    apple_data=pd.read_csv("../apple.csv")
    apple_data.sort("date",inplace=True)

    apple_inst = SimulatedInstrument("Apple","APPL", "stock")
    S=ThresholdTurningPoint("AppleHistorical", None, inst=apple_inst, funds=funds, simulated=True)
    for t, start, stop in zip(apple_data["date"],apple_data["open"],apple_data["close"]):
        if "/" not in t:
            continue
        year=int(t.split("/")[0])
        if (year<start_year) or (year>end_year):
            continue
        t2=t+" 9:30"
        apple_inst.update(t2,start)
        S.init(n,h,u)
        break
    for t, start, stop in zip(apple_data["date"],apple_data["open"],apple_data["close"]):
        if "/" not in t:
            continue
        year=int(t.split("/")[0])
        if (year<start_year) or (year>end_year):
            continue
        t2=t+" 9:30"
        S.update(t=t2,p=float(start))
        t2=t+" 16:00"
        S.update(t=t2,p=float(stop))
    # logger.info("Current fund is {}".format(str(S.funds)))
    # logger.info("Current unit is {}".format(S.units))
    # logger.info("Overall profit (if clearing now) is {}".format(str(S.funds+S.units*S.inst.price-100000)))
    # plt.figure(figsize=(40,20))
    # plt.plot(S.ts,S.ps,'k--*')
    # for oid, (direction,t1,p1,t2,p2) in S.orders.items():
        # if direction==1:
            # #selling
            # plt.annotate(str(oid)+'-',xy=(t1,p1), color="r")
            # plt.annotate(str(oid)+'-',xy=(t2,p2), color="r")
        # else:
            # plt.annotate(str(oid)+"+",xy=(t1,p1), color="g")
            # plt.annotate(str(oid)+"+",xy=(t2,p2), color="g")
    # plt.savefig("apple.png")

    return S

def ThresholdTurningPointSimulatorTwitter(funds=100000,n=20,h=1,u=400, start_year=2014, end_year=2016):

    twitter_data=pd.read_csv("../twitter.csv")
    twitter_data.sort("Date",inplace=True)

    twitter_inst = SimulatedInstrument("Twitter","TWIT", "stock")
    S=ThresholdTurningPoint("TwitterHistorical", None, inst=twitter_inst, funds=funds, simulated=True)
    for t, start, stop in zip(twitter_data["Date"],twitter_data["Open"],twitter_data["Close"]):
        if "-" not in t:
            continue
        year=int(t.split("-")[0])
        if year < start_year or year>end_year:
            continue
        t2=t+" 9:30"
        twitter_inst.update(t2,start)
        S.init(n,h,u)
        break
    for t, start, stop in zip(twitter_data["Date"],twitter_data["Open"],twitter_data["Close"]):
        if "-" not in t:
            continue
        year=int(t.split("-")[0])
        if year < start_year or year>end_year:
            continue
        t2=t+" 9:30"
        S.update(t=t2,p=float(start))
        t2=t+" 16:00"
        S.update(t=t2,p=float(stop))
    # logger.info("Current fund is {}".format(str(S.funds)))
    # logger.info("Current unit is {}".format(S.units))
    # logger.info("Overall profit (if clearing now) is {}".format(str(S.funds+S.units*S.inst.price-100000)))
    return S


if __name__=="__main__":
    ThresholdTurningPointSimulatorTwitter()
