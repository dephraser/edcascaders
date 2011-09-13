import rpyc

class FakeAsync:
    def __init__(self, value):
        self.value = value


class RpcClient:
    '''
    Wrapper around the functions that the server provides, this tries to pull
    some of the bulk and extra lines of code out of the gui classes 

    It also allows (mostly) the switching off of async to make it easier to get
    errors et al
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

        self.async = True

    def setAsync(self, enabled=True):
        self.async = enabled

    def _callFunction(self, function, callback, *args, **kwargs):
        if self.async:
            res = rpyc.async(function)(*args, **kwargs)
            if callback is not None:
                res.add_callback(callback)
        else:
            result = FakeAsync(function(*args, **kwargs))
            if callback is not None:
                callback(result)

    #--------------------------------------------------------------------------
    # simple functions used on startup
    def getCascaderList(self, callback):
        self._callFunction(self.user.getCascaderList, callback)

    def getSubjectList(self, callback):
        self._callFunction(self.user.getSubjectList, callback)

    #--------------------------------------------------------------------------
    # cascading related 
    def startCascading(self, callback=None):
        self._callFunction(self.user.startCascading, callback)

    def stopCascading(self, callback=None):
        self._callFunction(self.user.stopCascading, callback)

    def addSubjects(self, subjects):
        self._callFunction(self.user.addSubjects, None, subjects)

    def removeSubjects(self, subjects):
        self._callFunction(self.user.removeSubjects, None, subjects)

    #--------------------------------------------------------------------------

    def sendMessage(self, helpid, username, subject, message):
        self._callFunction(self.user.sendMessage, None, helpid, username, message)

    # messaging related
    def askForHelp(self, helpid, username, subject, problem, callback=None):
        res = rpyc.async(self.user.askForHelp)(helpid, username,
                                               subject, problem)
        if callback is not None:
            #the result from this is an async result, so we need to add another
            #callback
            res.add_callback(lambda result: result.add_callback(callback))
