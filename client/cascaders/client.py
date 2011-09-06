'''
Generic wrapper around the functions that the server provides, this 
tries to pull some of the bulk out of the gui classes

This requires wx, so that it can dispatch the events to the wx thread
'''

import rpyc
import wx

class RpcClient:
    def __init__(self, host, port, username, computerHostname):
        #does raise exceptions when cannot connect, 
        self.conn = rpyc.connect(host, port)
        bgsrv = rpyc.BgServingThread(self.conn)
  
        try:
            self.user = self.conn.root.userJoin(username, computerHostname, lambda: None)
        except ValueError:
            self.conn.close()
            self.conn = None
            raise

    #--------------------------------------------------------------------------
    # simple functions used on startup
    def getCascaderList(self, callback):
        res = rpyc.async(self.user.getCascaderList)()
        res.add_callback(lambda *args: wx.CallAfter(callback, *args))

    def getSubjectList(self, callback):
        res = rpyc.async(self.user.getSubjectList)()
        res.add_callback(lambda *args: wx.CallAfter(callback, *args))

    #--------------------------------------------------------------------------
    # cascading related 
    def startCascading(self, callback=None):
        res = rpyc.async(self.user.startCascading)()
        if callback is not None:
            res.add_callback(lambda *args: wx.CallAfter(callback, *args))

    def stopCascading(self, callback=None):
        res = rpyc.async(self.user.stopCascading)()
        if callback is not None:
            res.add_callback(lambda *args: wx.CallAfter(callback, *args))

    def addSubjects(self, subjects):
        rpyc.async(self.user.addSubjects)(subjects)

    def removeSubjects(self, subjects):
        rpyc.async(self.user.removeSubjects)(subjects)

    #--------------------------------------------------------------------------
    # messaging related
    def askForHelp(self, helpid, username, subject, problem, callback=None):
        res = rpyc.async(self.user.askForHelp)(helpid, username,
                                               subject, problem)
        if callback is not None:
            res.add_callback(lambda *args: wx.CallAfter(callback, *args))
