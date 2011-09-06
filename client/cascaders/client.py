import rpyc
import wx #just used for wx.CallAfter

class RpcClient:
    '''
    Wrapper around the functions that the server provides, this tries to pull
    some of the bulk and extra lines of code out of the gui classes 

    This requires wx, so that it can dispatch the events to the wx thread, 
    if we don't do this the GUI (obviosuly) breaks really badly.
    '''
    def __init__(self, host, port, username, computerHostname):
        #Nb: does raise exceptions when cannot connect, 
        self.conn = rpyc.connect(host, port)

        #this watches on ANOTHER THREAD for incomming data.
        bgsrv = rpyc.BgServingThread(self.conn)
  
        try:
            self.user = self.conn.root.userJoin(username,
                                                computerHostname,
                                                lambda: None)
        except ValueError:
            self.conn.close()
            self.conn = None
            raise

    def _addCallback(resource, callback):
        ''' Safe way of calling back to the wx thread '''
        if callback is not None:
            resource.add_callback(lambda *args: wx.CallAfter(callback, *args))

    #--------------------------------------------------------------------------
    # simple functions used on startup
    def getCascaderList(self, callback):
        res = rpyc.async(self.user.getCascaderList)()
        res.add_callback(lambda *args: wx.CallAfter(callback, *args))

    def getSubjectList(self, callback):
        res = rpyc.async(self.user.getSubjectList)()
        self._addCallback(resource, callback)

    #--------------------------------------------------------------------------
    # cascading related 
    def startCascading(self, callback=None):
        res = rpyc.async(self.user.startCascading)()
        self._addCallback(resource, callback)

    def stopCascading(self, callback=None):
        res = rpyc.async(self.user.stopCascading)()
        self._addCallback(resource, callback)

    def addSubjects(self, subjects):
        rpyc.async(self.user.addSubjects)(subjects)

    def removeSubjects(self, subjects):
        rpyc.async(self.user.removeSubjects)(subjects)

    #--------------------------------------------------------------------------
    # messaging related
    def askForHelp(self, helpid, username, subject, problem, callback=None):
        res = rpyc.async(self.user.askForHelp)(helpid, username,
                                               subject, problem)
        self._addCallback(resource, callback)
