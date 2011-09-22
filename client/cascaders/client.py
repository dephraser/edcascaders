from twisted.spread import pb
from twisted.internet import reactor

from logging import debug

class RpcClient:
    '''
    Wrapper around the functions that the server provides, this tries to pull
    some of the bulk and extra lines of code out of the gui classes 

    To try and maintin a responsive interface when connecting, it is possible
    to call functions on the server, they will just be queued and called
    when login has completed
    '''
    def __init__(self, service, host, port, username, computerHostname):
        self.factory = pb.PBClientFactory()
        reactor.connectTCP(host, port, self.factory)

        self.connectionErrFuncs = [] #functions to be called if conn failed
        self.loginErrFuncs = [] #funcs to be called if login failed
        self.loginFuncs = [] #functions to be called on login sucess

        self.queuedFunctions = [] #list of functions queued until login
        
        self.root = None #class that holds the primary server functions

        #connect to the server
        deferred = self.factory.getRootObject()
        deferred.addCallback(self._onGetRootObj,
                             service,
                             username,
                             computerHostname)
        deferred.addErrback(self._callConnectErrFunctions)

    def _onGetRootObj(self, obj, service, username, computerHostname):
        self.root = obj
        d = self.root.callRemote('userJoin',
                                 service,
                                 username,
                                 computerHostname)
        d.addCallback(self._callLoginFunctions)
        d.addErrback(self._callLoginErrFunctions)

    #---------------------------------------------------------------------------
    def _callLoginFunctions(self, *a):
        '''
        This is called on login, it also cleans up the queued functions as
        they are now possible to call
        '''
        [f() for f in self.loginFuncs]

        for details in self.queuedFunctions:
            self._callFunction(details['function'], details['callback'],
                               *details['args'], **details['kwargs'])
        self.queuedFunctions = []

    def _callLoginErrFunctions(self, *a):
        [f() for f in self.loginErrFuncs]

    def _callConnectErrFunctions(self, *a):
        [f() for f in self.connectionErrFuncs]

    def registerLoginErrCallback(self, callback):
        self.loginErrFuncs.append(callback)

    def registerConnectErrCallback(self, callback):
        self.connectionErrFuncs.append(callback)

    def registerLoginCallback(self, callback):
        ''' This is in most cases not required, as calls a queued '''
        self.connectionErrFuncs.append(callback)

    #---------------------------------------------------------------------------

    def _callFunction(self, function, callback, *args, **kwargs):
        '''
        This guarentees that at some point the function will be called,
        as long as there are no errors with setting up the connection

        This makes using the client nicer as it is still possible to add/remove
        subjects and on connection everything is just synced
        '''
        if self.root is None:
            self.queuedFunctions.append({
                'function' : function,
                'args' : args,
                'kwargs' : kwargs,
                'callback' : callback,
            })
        else:
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
