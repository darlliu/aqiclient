from flask import Flask
from flask import request, url_for, redirect, session, escape, abort
from flask import render_template
from objects import *
app = Flask(__name__)
app.secret_key= "ZDFGHDHDFGHJGHK#@#$R%TWDFGSDFASDA"
import argparse
import json
from sim import *
from collections import OrderedDict

@app.route('/', methods=['POST', 'GET'])
def Main():
    #filter user here
    return render_template('display.html')

@app.route('/data', methods=['POST','GET'])
def Data():
    stock=request.form.get("stock","apple")
    n=float(request.form.get("n",20))
    h=float(request.form.get("h",1))
    start=int(request.form.get("start_year",2014))
    end=int(request.form.get("end_year",2016))
    funds=float(request.form.get("funds",100000))
    units=float(request.form.get("units",4000))
    if stock=="apple":
        S=ThresholdTurningPointSimulatorApple(funds=funds,n=n,h=h,u=units, start_year=start, end_year=end)
    else:
        S=ThresholdTurningPointSimulatorTwitter(funds=funds,n=n,h=h,u=units, start_year=start, end_year=end)
    output={}
    data={}
    data["cols"]=[
            {"id":"","label":"Time","pattern":"","type":"datetime"},
            {"id":"","label":"Price","pattern":"","type":"number"},
            ]
    data["rows"]=[]
    for t,p in zip(S.ts, S.ps):
        d="Date({},{},{},{})".format(t.year,t.month,t.day,t.hour)
        data["rows"].append({"c":[{"v":d, "f":None},{"v":p,"f":None}]})
    output["chart"]=data

    data={}
    data["cols"]=[
            {"id":"","label":"Time","pattern":"","type":"datetime"},
            {"id":"","label":"Funds","pattern":"","type":"number"},
            {"id":"","label":"Units","pattern":"","type":"number"},
            {"id":"","label":"Gains","pattern":"","type":"number"},
            ]
    data["rows"]=[]
    for t,p1,p2,p3 in zip(S.ts, S.funds_series,S.units_series, S.gains_series):
        d="Date({},{},{},{})".format(t.year,t.month,t.day,t.hour)
        data["rows"].append({"c":[{"v":d, "f":None},{"v":p1,"f":None},{"v":p2,"f":None},{"v":p3,"f":None}]})
    output["chart2"]=data

    data={}
    data["cols"]=[
            {"id":"","label":"ID","pattern":"","type":"number"},
            {"id":"","label":"Status","pattern":"","type":"string"},
            {"id":"","label":"Direction","pattern":"","type":"string"},
            {"id":"","label":"Tbegin","pattern":"","type":"datetime"},
            {"id":"","label":"Tend","pattern":"","type":"datetime"},
            {"id":"","label":"Pt","pattern":"","type":"number"},
            {"id":"","label":"Popt","pattern":"","type":"number"},
            {"id":"","label":"Pend","pattern":"","type":"number"},
            {"id":"","label":"Margin","pattern":"","type":"number"},
            ]
    data["rows"]=[]
    for s in S.routines:
        if s.cleared:
            status="Cleared"
        elif s.terminated:
            status="Terminated"
        else:
            status="Running"
        if s.direction==-1:
            direction="Selling"
        else:
            direction="Buying"
        t=s.t
        d1="Date({},{},{},{})".format(t.year,t.month,t.day,t.hour)
        t=s.tend
        d2="Date({},{},{},{})".format(t.year,t.month,t.day,t.hour)
        data["rows"].append({"c":[{"v":s.sid, "f":None},{"v":status,"f":None},{"v":direction,"f":None},{"v":d1,"f":None},{"v":d2,"f":None},
            {"v":s.pt,"f":None},{"v":s.opt,"f":None},{"v":s.pend,"f":None},{"v":s.pend-s.pt,"f":None}]})
    output["table"]=data

    return json.dumps(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web Server for AqiClient(Simulator)')
    parser.add_argument('--port', type=int, help='Port number for deployment')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')

    args = parser.parse_args()
    if args.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    app.run(host='0.0.0.0',port=args.port,debug=args.debug)
