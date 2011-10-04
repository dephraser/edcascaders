'''
Set of code that is not dependant on the gui
'''
from collections import defaultdict
from logging import debug, info, warn, error

import service
import client

from util import CallbackMixin

#-------------------------------------------------------------------------------
#constants
PORT = 5010
#HOST = 'kazila.jacobessex.com'
HOST = 'localhost'
#-------------------------------------------------------------------------------

class CascadersData(object):
    ''' Manages a list of cascaders and provides helpful functions '''

    def __init__(self, locator, username):
        '''
        locator is a object that implements labFromHostname.

        username is the current users username. This is excluded from
        results so that you are never displayed as a cascader
        '''
        self.locator = locator
        self.username = username
        self.cascaders = {}

    def __str__(self):
        return str(self.cascaders)

    def addCascader(self, username, host, subjects):
        '''
        >>> cd = CascadersData(None, 'me')
        >>> cd.addCascader('remote', 'remotehost', ['subject'])
        >>> cd.findCascader(username='remote')
        ('remote', ('remotehost', set(['subject'])))

        Key is on the username...
        >>> cd = CascadersData(None, 'me')
        >>> cd.addCascader('remote', 'remotehost', ['subject'])
        >>> cd.addCascader('remote', 'otherhost', ['subject'])
        >>> cd.findCascader(username='remote')
        ('remote', ('otherhost', set(['subject'])))

        Subjects are a set
        >>> cd = CascadersData(None, 'me')
        >>> cd.addCascader('remote', 'remotehost', ['a', 'a', 'b'])
        >>> cd.findCascader(username='remote')
        ('remote', ('remotehost', set(['a', 'b'])))
        '''
        try:
            _, curSubjects = self.cascaders[username]
            self.cascaders[username] = (host, set(subjects) | curSubjects)
        except KeyError:
            self.cascaders[username] = (host, set(subjects))

    def removeCascader(self, username):
        try:
            del self.cascaders[username]
        except KeyError:
            warn('Cascader that left didn\'t exist')

    def addCascaderSubjects(self, username, subjects):
        '''
        Adding the same subject again is fine
        >>> cd = CascadersData(None, 'me')
        >>> cd.addCascader('remote', 'remotehost', ['a'])
        >>> cd.addCascaderSubjects('remote', ['a'])
        >>> cd.findCascader(username='remote')
        ('remote', ('remotehost', set(['a'])))

        >>> cd = CascadersData(None, 'me')
        >>> cd.addCascader('remote', 'remotehost', [])
        >>> cd.addCascaderSubjects('remote', ['a'])
        >>> cd.findCascader(username='remote')
        ('remote', ('remotehost', set(['a'])))
        '''
        try:
            host, curSubjects = self.cascaders[username]
            self.cascaders[username] = (host, curSubjects | set(subjects))
        except KeyError:
            warn('Cascader (%s) that added subjects '
                 'didn\'t exist' % username)
            self.cascaders[username] = (None, set(subjects))

    def removeCascaderSubjects(self, username, subjects):
        debug('Cascader %s removed subjects %s' % (username, subjects))
        try: 
            host, curSubjects = self.cascaders[username]
            self.cascaders[username] = host, curSubjects - set(subjects)
        except KeyError:
            warn('Tried to remove subjects from cascader %s, '
                 'prob not cascading' % username)

    def findCascaders(self, lab=None, subjects=None, host=None,
                            includeMe = False):
        '''
        Find all cascaders that match the given patterns, although
        this will not return any cascaders that are not cascading in 
        any subjects

        TODO really slow, not sure it matters

        >>> cd = CascadersData(None, 'me')
        >>> cd.addCascader('remote', 'remotehost', [])
        >>> cd.findCascader(username='remote')
        '''
        for user, (cascHost, cascSubjects) in self.cascaders.iteritems():
            if len(cascSubjects) == 0:
                continue

            if includeMe == False and user == self.username:
                continue

            if host and host != cascHost:
                continue

            if lab and self.locator.labFromHostname(cascHost) != lab:
                continue

            if (subjects and
                    len(set(subjects).intersection(set(cascSubjects))) == 0):
                continue

            yield user, (host, cascSubjects)

    def findCascader(self, username=None, includeMe=False, **kwargs):
        ''' Wrapper around findCascaders, returns the first match or None '''
        if username is not None:
            if len(kwargs):
                error('Username not supported with other args')
                return None
            try:
                host, subjects = self.cascaders[username]
                if len(subjects) == 0: 
                    return None
                if includeMe == False and username == self.username:
                    return None
                return username, (host, subjects)
            except KeyError:
                warn('Couldn\'t find cascader with username: ' % username)
                return None

        try:
            return self.findCascaders(includeMe=includeMe, **kwargs).next()
        except StopIteration:
            return None

#-------------------------------------------------------------------------------

class CascaderModel(CallbackMixin):
    '''
    This is the model for the main interface, it holds and provides most of the
    data for cascaders. It doesn't handle conversations

    Data communication is done through callbacks. Which are either registered
    using the methods in this class or in the case of calls to the server
    they are added to the deferred result.
    '''
    def __init__(self, locator, username, hostname):
        CallbackMixin.__init__(self)

        self.cascaders = CascadersData(locator, username)

        self.service = s = service.RpcService()
        self.client = client.RpcClient(self.service, HOST,
                                       PORT, username, hostname)

        s.registerOnCascaderRemovedSubjects(self.onCascaderRemovedSubjects)
        s.registerOnCascaderAddedSubjects(self.onCascaderAddedSubjects)

        s.registerOnCascaderJoined(self.onCascaderJoined)
        s.registerOnCascaderLeft(self.onCascaderLeft)

        s.registerUserAskingForHelp(self.onUserAskingForHelp)

        self.registerOnLogin(self.onLogin)

        self.subjects = set()
        self.cascadeSubjects = set()
        self.cascading = False

        self.username = username
        self.hostname = hostname

    def __getattribute__(self, name):
        ''' 
        Both the client and the service have the ability to register some
        callbacks, this allows those callbacks to be used without
        having to expose anything beyond this class
        '''
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            if name.startswith('register'):
                if hasattr(self.client, name):
                    return self.client.__getattribute__(name)
                elif hasattr(self.service, name):
                    return self.service.__getattribute__(name)
            raise

    def getCascaderData(self):
        return self.cascaders
    #--------------------------------------------------------------------------
    # Service callbacks
    def onCascaderAddedSubjects(self, username, subjects):
        debug('Cascader %s added subjects %s' % (username, subjects))
        self.cascaders.addCascaderSubjects(username, subjects)
        self._callCallbacks('cascaderschanged', self.cascaders)

    def onCascaderRemovedSubjects(self, username, subjects):
        debug('Cascader %s removed subjects %s' % (username, subjects))
        self.cascaders.removeCascaderSubjects(username, subjects)
        self._callCallbacks('cascaderschanged', self.cascaders)

    def onCascaderJoined(self, username, hostname, subjects):
        debug('New cascader: (%s, (%s, %s)' % (username,
                                               hostname,
                                               str(subjects)))
        self.cascaders.addCascader(username, hostname, subjects)
        self._callCallbacks('cascaderschanged', self.cascaders)

    def onCascaderLeft(self, username):
        debug('Cascader left: %s' % username)
        self.cascaders.removeCascader(username)
        self._callCallbacks('cascaderschanged', self.cascaders)

    def onUserAskingForHelp(self,  helpid, username, host,
                            subject, description):
        self._callCallbacks('userasking', helpid, username,
                            host, subject, description)
    #--------------------------------------------------------------------------
    def registerOnCascaderChanged(self, function):
        self._addCallback('cascaderschanged', function)

    def registerOnSubjectChanged(self, function):
        self._addCallback('subjectschanged', function)

    def registerOnUserAskingForHelp(self, function):
        self._addCallback('userasking', function)
    #--------------------------------------------------------------------------

    def connect(self):
        debug('Connecting...')
        return self.client.connect()

    def login(self):
        debug('Logging in...')
        def subject(result):
            debug('Got subjects from login')
            self.subjects = set([x for x in result])
            self._callCallbacks('subjectschanged', self.subjects)

        def casc(result):
            debug('Got cascaders from login: %s' % str(result))
            for usr, host, sub in result:
                self.cascaders.addCascader(usr, host, sub)
            self._callCallbacks('cascaderschanged', self.cascaders)

        sl = lambda *a: self.client.getSubjectList().addCallback(subject)
        cl = lambda *a: self.client.getCascaderList().addCallback(casc)

        d = self.client.login()
        d.addCallback(cl)
        d.addCallback(sl)

        return d

    def onLogin(self, *a):
        '''
        This tries for force everything to the way it was before
        the server disconnected
        '''
        debug('Now logged in, trying to restore settings')
        if self.isCascading():
            self.startCascading()
        self.addSubjects(self.cascadeSubjects)

    #--------------------------------------------------------------------------
    def _handleServerLost(fn):
        ''' decorator TODO really not sure this is needed '''
        def function(self, *args, **kwargs):
            try:
                return fn(self, *args, **kwargs)
            except client.NotConnected as e:
                warn('Server was lost')
                self._serverLost()
                return e.getDeferred()
        return function

    def _serverLost(self):
        '''
        This should be called when the connection to the server is lost
        it attempts to reconnect to the server
        '''
        debug('Caught sever lost')

        def connected():
            self._login()

        def connectError(reason):
            debug('Trying to connect...')
            callConnect()
            return False

        def callConnect():
            d = self.client.connect()
            d.addErrback(lambda r: gobject.timeout_add(5000, connectError, r))
            d.addCallback(connected)

        callConnect()

    #--------------------------------------------------------------------------
    def isCascading(self):
        return self.cascading

    @_handleServerLost
    def startCascading(self):
        self.cascading = True
        return self.client.startCascading()

    @_handleServerLost
    def stopCascading(self):
        self.cascading = False
        return self.client.stopCascading()

    #--------------------------------------------------------------------------
    def cascadingSubjects(self):
        return self.cascadeSubjects

    @_handleServerLost
    def addSubjects(self, subjects):
        '''
        This doesn't try to mimize data transfer by checking
        subjects are valid as we may not have retrived the
        subjects by the time this is called
        '''
        self.cascadeSubjects = self.cascadeSubjects | set(subjects)
        debug('Adding subjects: %s' % str(subjects))
        return self.client.addSubjects(subjects)

    @_handleServerLost
    def removeSubjects(self, subjects):
        self.cascadeSubjects = self.cascadeSubjects - set(subjects)
        return self.client.removeSubjects(subjects)

    @_handleServerLost
    def askForHelp(self, helpid, username, subject, problem):
        return self.client.askForHelp(helpid, username, subject, problem)

    @_handleServerLost
    def sendMessage(self, helpid, toUsername, message):
        '''
        This shouldn't really be here I don't think. It isn't abstract enough
        '''
        return self.client.sendMessage(helpid, toUsername, message)
