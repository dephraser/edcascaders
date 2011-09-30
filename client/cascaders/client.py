from twisted.spread import pb
from twisted.internet import reactor

class NotConnected(pb.DeadReferenceError):
    pass


class DeferredCall(object):
    ''' Simple wrapper around twisteds deferred call '''
    def __init__(self, deferred):
        self.deferred = deferred

        self.callbacks = []
        self.errbacks = []

    def addCallback(self, function, *args):
        self.callbacks.append((function, args))
        self.deferred.addCallback(function, *args)

    def addErrCallback(self, function, *args):
        self.errbacks.append((function, args))
        self.deferred.addErrback(function, *args)


class QueuedDeferredCall(DeferredCall):
    '''
    This represents a deferred call that hasn't yet been sent to the server

    This is mainly used so we can make calls to the server before the server
    has connected which simplifies the main interface
    '''
    def __init__(self, function, *args, **kwargs):
        super(QueuedDeferredCall, self).__init__(None)
        self.toCall = (function, args, kwargs)
        self.callbacks = []
        self.errCallbacks = []

    def addCallback(self, function, *args):
        if self.deferred is None:
            self.callbacks.append((function, args))
        else:
            super(QueuedDeferredCall, self).addCallback(function, *args)

    def addErrCallback(self, function, *args):
        if self.deferred is None:
            self.errCallbacks.append((function, args))
        else:
            super(QueuedDeferredCall, self).addErrCallback(function, *args)

    def call(self, function):
        '''
        function - A function used to actually call the server, this should
        accept a functionname and then arbatary arguments
        '''
        assert self.deferred is None
        self.deferred = function(self.toCall[0], #name
                                 *self.toCall[1], #args
                                 **self.toCall[2]) #kw args
        #pass them all back up
        for f, a in self.callbacks:
            super(QueuedDeferredCall, self).addCallback(f, *a)

        for f, a in self.errCallbacks:
            super(QueuedDeferredCall, self).addErrCallback(f, *a)


class DeferredResultWrapper(object):
    '''
    This class is a wrapper around a deferred object that slightly alters
    it so that provides a transparant interface for the server returing a deferred
    rather than the real result.

    This is used when the server makes a call to another client and returns
    that deferred object as the result

    This is a wrapper so that it can cope with a queued defered object
    '''
    def __init__(self, deferred):
        self.deferred = deferred

    def __getattribute__(self, name):
        if name in ('addCallback', 'deferred'):
            return object.__getattribute__(self, name)
        return self.deferred.__getattribue__(name)

    def addCallback(self, function, *args, **kwargs):
        function = lambda deferred: deferred.addCallback(*args, **kwargs)
        self.deferred.addCallback(function)


class RpcClient:
    '''
    Wrapper around the functions that the server provides, this tries to pull
    some of the bulk and extra lines of code out of the gui classes 

    To try and maintin a responsive interface when connecting, it is possible
    to call functions on the server, they will just be queued and called
    when login has completed
    '''
    def __init__(self, service, host, port, username, computerHostname):
        '''
        service - the service that the client should provide
        host
        port 
        username - the users login name, will be unique within the system
        computerHostname - the hostname of the computer
        '''
        self.host = host 
        self.port = port

        self.connectionErrFuncs = [] #functions to be called if conn failed
        self.loginErrFuncs = [] #funcs to be called if login failed
        self.loginFuncs = [] #functions to be called on login sucess

        self.queuedFunctions = [] #list of functions queued until login
        
        self.server = None #class that holds the primary server functions

        self.service = service
        self.username = username
        self.computerHostname = computerHostname

        self.factory = pb.PBClientFactory()

    def connect(self):
        #connect to the server
        reactor.connectTCP(self.host, self.port, self.factory)

        try:
            deferred = self.factory.getRootObject()
        except pb.DeadReferenceError:
            raise NotConnected

        deferred.addCallback(self._userLogin,
                             self.service,
                             self.username,
                             self.computerHostname)

        deferred.addErrback(self._callConnectErrFunctions)

    def _userLogin(self, root, service, username, computerHostname):
        d = root.callRemote('userJoin',
                             service,
                             username,
                             computerHostname)
        d.addCallback(self._callLoginFunctions)
        d.addErrback(self._callLoginErrFunctions)

    #---------------------------------------------------------------------------
    def _callLoginFunctions(self, userService):
        '''
        This is called on login, it also cleans up the queued functions as
        they are now possible to call
        '''
        self.server = userService

        [f() for f in self.loginFuncs]
        self.loginFuncs = []
        self.loginErrFuncs = []
        self.connectionErrFuncs = []

        for deferred in self.queuedFunctions:
            deferred.call(self._callFunction)
        self.queuedFunctions = []

    def _callLoginErrFunctions(self, reason):
        [f(reason) for f in self.loginErrFuncs]
        self.loginFuncs = []
        self.loginErrFuncs = []
        self.connectionErrFuncs = []

    def _callConnectErrFunctions(self, reason):
        [f(reason) for f in self.connectionErrFuncs]
        self.loginFuncs = []
        self.loginErrFuncs = []
        self.connectionErrFuncs = []

    def registerLoginErrCallback(self, callback):
        self.loginErrFuncs.append(callback)

    def registerConnectErrCallback(self, callback):
        self.connectionErrFuncs.append(callback)

    def registerLoginCallback(self, callback):
        ''' This is in most cases not required, as calls a queued '''
        self.loginFuncs.append(callback)

    #---------------------------------------------------------------------------

    def _callFunction(self, function, *args, **kwargs):
        '''
        This guarentees that at some point the function will be called,
        as long as there are no errors with setting up the connection

        This makes using the client nicer as it is still possible to add/remove
        subjects and on connection everything is just synced
        '''
        if self.server is None:
            qdc = QueuedDeferredCall(function, *args, **kwargs)
            self.queuedFunctions.append(qdc)
            return qdc
        else:
            try:
                return DeferredCall(self.server.callRemote(function, *args, **kwargs))
            except pb.DeadReferenceError:
                self.server = None

                qdc = QueuedDeferredCall(function, *args, **kwargs)
                self.queuedFunctions.append(qdc)

                raise NotConnected('Failed to call ' + function)

    #--------------------------------------------------------------------------
    # simple functions used on startup
    def getCascaderList(self):
        return self._callFunction('getCascaderList')

    def getSubjectList(self):
        return self._callFunction('getSubjectList')

    #--------------------------------------------------------------------------
    # cascading related 
    def startCascading(self):
        return self._callFunction('startCascading')

    def stopCascading(self):
        return self._callFunction('stopCascading')

    def addSubjects(self, subjects):
        return self._callFunction('addSubjects', subjects)

    def removeSubjects(self, subjects):
        return self._callFunction('removeSubjects', subjects)

    #--------------------------------------------------------------------------
    # messaging related
    def sendMessage(self, helpid, username, subject, message):
        return self._callFunction('sendMessage', helpid, username, message)

    def askForHelp(self, helpid, username, subject, problem):
        '''
        Ask for help is implemented slightly diffferenetly from most other
        functions on the server, in that it returns a deferred as its result
        '''
        return DeferredResultWrapper(self._callFunction('askForHelp',
                                                        helpid,
                                                        username,
                                                        subject,
                                                        problem))
    #--------------------------------------------------------------------------
    def logout(self):
        return self._callFunction('logout')
