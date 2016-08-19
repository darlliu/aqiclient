import urllib,urllib2
import httplib
import json

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

def RESTAction(conn, url, action="GET",**kwargs):
    params = json.dumps(kwargs)
    if action not in ["POST","GET","PUT"]:
        raise ValueError("Cannot perform this action: {}".format(action))
    if action == "POST":
        req = conn.request(action, url, params, {"Content-Type":"application/json"})
    elif action == "GET":
        req = conn.request(action, url)
    else:
        raise NotImplemented("This method is not supported yet")      
    res = conn.getresponse()
    if res.status == 200:        
        return res.read()
    else:
        print "ERR: {}".format(res.status)
        return None

class Instrument(object):
    """
    Instrument is a stock or future, it associates with itself
    data such as prices and operations such as inquire, set up order etc
    Instruments need to have owners to function, the ones that don't are non-tradable
    """
    def __init__(self, id, itype=None, port=None):
        if itype not in ["future","stock"]:
            raise ValueError("Type of Instrument is not supported : {}".format(itype))
        self.type = itype
        self.id = id
        self.port = port
        self.update()
        return

    def update(self):
        """
        Obtains updated information for the instrument
        """
        return

    def orderShort(self, units):
        pass
    
    def orderLong(self, units):
        pass

class Portfolio(object):
    """
    Portfolio is a profile that exists on the serve side, and is associated with instruments
    It contains pools of instruments with varying units
    """
    pass

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

    conn = RESTConnection()
    print RESTAction(conn.h, "/api/user")
    #print RESTAction(conn.h, "/api/instruments") <-reads a lot of stuff!
