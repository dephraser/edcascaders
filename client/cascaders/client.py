import rpyc
import gtk

class RpcClient:
    '''
    Wrapper around the functions that the server provides, this tries to pull
    some of the bulk and extra lines of code out of the gui classes 

    This requires wx, so that it can dispatch the events to the wx thread, 
    if we don't do this the GUI (obviosuly) breaks really badly.
    '''
    def __init__(self, service, host, port, username, computerHostname):
        #Nb: does raise exceptions when cannot connect, 
        self.conn = rpyc.connect(host, port, service = service)

        try:
            self.user = self.conn.root.userJoin(username,
                                                computerHostname,
                                                lambda: None)
        except ValueError:
            self.conn.close()
            self.conn = None
            raise

    def _addCallback(self, resource, callback):
        ''' Safe way of calling back to the gtk thread '''
        if callback is not None:
            resource.add_callback(callback)

    #--------------------------------------------------------------------------
    # simple functions used on startup
    def getCascaderList(self, callback):
        res = rpyc.async(self.user.getCascaderList)()
        self._addCallback(res, callback)

    def getSubjectList(self, callback):
        res = rpyc.async(self.user.getSubjectList)()
        self._addCallback(res, callback)

    #--------------------------------------------------------------------------
    # cascading related 
    def startCascading(self, callback=None):
        res = rpyc.async(self.user.startCascading)()
        self._addCallback(res, callback)

    def stopCascading(self, callback=None):
        res = rpyc.async(self.user.stopCascading)()
        self._addCallback(res, callback)

    def addSubjects(self, subjects):
        rpyc.async(self.user.addSubjects)(subjects)

    def removeSubjects(self, subjects):
        rpyc.async(self.user.removeSubjects)(subjects)

    #--------------------------------------------------------------------------
    # messaging related
    def askForHelp(self, helpid, username, subject, problem, callback=None):
        res = rpyc.async(self.user.askForHelp)(helpid, username,
                                               subject, problem)
        self._addCallback(res, callback)
