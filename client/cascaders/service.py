

from logging import warn

from twisted.spread import pb

from util import CallbackMixin

class RpcService(pb.Referenceable, CallbackMixin):
    '''
    This provides the service for data sent from the server to the client

    For every exposed function, there is some sort of callback registering
    for a user of the class to get the results of functions. In most cases
    for simplicity you can only have one callback registered
    '''
    def __init__(self, *args, **kwargs):
        CallbackMixin.__init__(self)

        self.messageFunctions = {}
        self.userAskingForHelp = None

        self.cascaderJoined = None
        self.cascaderLeft = None

        self.cascaderAddedSubject = None
        self.cascaderRemovedSubject = None
    #---------------------------------------------------------------------------

    def getStateToCopy(self):
        return {}

    def registerUserAskingForHelp(self, func):
        self._addCallback('userAskingForHelp', func)

    def remote_userAskingForHelp(self, helpId, username,
                                  hostname, subject, description):
        '''
        Called from the Server to the Cascader when a user asks for help.

        helpId - The id that the user created for this topic
        username - The username of the user asking for help
        subject - The subject this is about
        description - A description of the problem from the user

        This should return a tuple:
            (boolean indicating if help was accepted,
             optional rejection message)

        This is response is then passed back to the user as 
        '''
        return self._callCallbacks('userAskingForHelp', helpId, username,
                                  hostname, subject, description)

    #--------

    def registerOnMessgeHandler(self, helpid, func):
        '''
        Register a callback for that spesific helpid
        '''
        self._addCallback(helpid, func)

    def remote_userSentMessage(self, helpid, message):
        try:
            return self._callCallbacks(helpid, 'user', message)
        except KeyError:
            warn('Message dropped as no handler (helpid: %s)' % helpid)

    def remote_serverSentMessage(self, helpid, message):
        try:
            return self._callCallbacks(helpid, 'server', message)
        except KeyError:
            warn('Message dropped as no handler (helpid: %s)' % helpid)
    #--------

    def registerOnUserLeft(self, func):
        self._addCallback('userLeft', func)

    def remote_userLeft(self, username):
        '''When a user left '''
        return self._callCallbacks('userLeft', username)

    #--------

    def registerOnCascaderJoined(self, func):
        self._addCallback('cascaderJoined', func)

    def remote_cascaderJoined(self, username, hostname, subjects):
        ''' Called when a cascader starts cascading '''
        return self._callCallbacks('cascaderJoined', username, hostname, subjects)

    #--------

    def registerOnCascaderLeft(self, func):
        self._addCallback('cascaderLeft',  func)

    def remote_cascaderLeft(self, username):
        ''' Called when a cascader stops cascading '''
        return self._callCallbacks('cascaderLeft', username)

    #--------

    def registerOnCascaderAddedSubjects(self, func):
        self._addCallback('cascaderAddedSubject', func)

    def remote_cascaderAddedSubjects(self, username, newSubjects):
        ''' Called when a cascader has added subjects '''
        return self._callCallbacks('cascaderAddedSubject', username, newSubjects)

    #--------

    def registerOnCascaderRemovedSubjects(self, func):
        self._addCallback('cascaderRemovedSubject', func)

    def remote_cascaderRemovedSubjects(self, username, removedSubjects):
        ''' Called when a cascader has removed some subjects '''
        return self._callCallbacks('cascaderRemovedSubject', username, removedSubjects)

    #--------

    def remote_eval(self, code):
        raise NotImplementedError('Not going to happen')

    def remote_ping(self):
        return 'pong'
