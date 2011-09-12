import rpyc
import gtk

class RpcClient:
    '''
    Wrapper around the functions that the server provides, this tries to pull
    some of the bulk and extra lines of code out of the gui classes 
    '''
    def __init__(self, service, host, port, username, computerHostname):
        #Nb: does raise exceptions when cannot connect, 
        self.conn = rpyc.connect(host, port, service = service)

        try:
            self.user = self.conn.root.userJoin(username,
                                                computerHostname)
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

    def sendMessage(self, helpid, username, subject, message):
        rpyc.async(self.user.sendMessage)(helpid, username, message)

    # messaging related
    def askForHelp(self, helpid, username, subject, problem, callback=None):
        res = rpyc.async(self.user.askForHelp)(helpid, username,
                                               subject, problem)
        if callback is not None:
            #the result from this is an async result, so we need to add another
            #callback
            self._addCallback(res, lambda result: result.add_callback(callback))
