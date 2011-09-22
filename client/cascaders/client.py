from twisted.spread import pb
from twisted.internet import reactor

class RpcClient:
    '''
    Wrapper around the functions that the server provides, this tries to pull
    some of the bulk and extra lines of code out of the gui classes 

    It also allows (mostly) the switching off of async to make it easier to get
    errors et al
    '''
    def __init__(self, service, host, port, username, computerHostname):
        self.factory = pb.PBClientFactory()
        reactor.connectTCP(host, port, self.factor)
        
        self.root = None

        #may take some time to connect, this handles the callback when connected
        deferred = factory.getRootObject()

        deferred.addCallback(self._onGetRoobObj,
                             service,
                             username,
                             computerHostname)

    def _onGetRootObj(self, obj, service, username, computerHostname):
        self.root = obj
        d = self.root.callRemote('userJoin',
                                 service,
                                 username,
                                 computerHostname)
        d.addCallback(self._onLogin)

    def _onLogin(self):
        pass

    def _callFunction(self, function, callback, *args, **kwargs):
        d = self.root.callRemote(function, *args, **kwargs)
        if callback is not None:
            d.addCallback(callback)

    #--------------------------------------------------------------------------
    # simple functions used on startup
    def getCascaderList(self, callback):
        self._callFunction('getCascaderList', callback)

    def getSubjectList(self, callback):
        self._callFunction('getSubjectList', callback)

    #--------------------------------------------------------------------------
    # cascading related 
    def startCascading(self, callback=None):
        self._callFunction('startCascading', callback)

    def stopCascading(self, callback=None):
        self._callFunction('stopCascading', callback)

    def addSubjects(self, subjects):
        self._callFunction('addSubjects', None, subjects)

    def removeSubjects(self, subjects):
        self._callFunction('removeSubjects', None, subjects)

    #--------------------------------------------------------------------------
    # messaging related
    def sendMessage(self, helpid, username, subject, message):
        self._callFunction('sendMessage', None, helpid, username, message)

    def askForHelp(self, helpid, username, subject, problem, callback=None):
        self._callFunction('askForHelp', callback,
                           helpid, username, subject, problem)
