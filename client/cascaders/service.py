

from logging import warn

from twisted.spread import pb

class RpcService(pb.Referenceable):
    '''
    This provides the service for data sent from the server to the client

    For every exposed function, there is some sort of callback registering
    for a user of the class to get the results of functions. In most cases
    for simplicity you can only have one callback registered
    '''
    def __init__(self, *args, **kwargs):
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
        self.userAskingForHelp = func

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
        return self.userAskingForHelp(helpId, username,
                                      hostname, subject, description)

    #--------

    def registerOnMessgeHandler(self, helpid, func):
        '''
        Register a callback for that spesific helpid
        '''
        self.messageFunctions[helpid] = func

    def remote_userSentMessage(self, helpid, message):
        try:
            return self.messageFunctions[helpid]('user', message)
        except KeyError:
            warn('Message dropped as no handler (helpid: %s)' % helpid)

    def remote_serverSentMessage(self, helpid, message):
        try:
            return self.messageFunctions[helpid]('server', message)
        except KeyError:
            warn('Message dropped as no handler (helpid: %s)' % helpid)

    #--------
    
    def registerOnCascaderJoined(self, func):
        self.cascaderJoined = func

    def remote_cascaderJoined(self, username, hostname, subjects):
        ''' Called when a cascader starts cascading '''
        return self.cascaderJoined(username, hostname, subjects)

    #--------

    def registerOnCascaderLeft(self, func):
        self.cascaderLeft = func

    def remote_cascaderLeft(self, username):
        ''' Called when a cascader stops cascading '''
        return self.cascaderLeft(username)

    #--------

    def registerOnCascaderAddedSubjects(self, func):
        self.cascaderAddedSubject = func

    def remote_cascaderAddedSubjects(self, username, newSubjects):
        ''' Called when a cascader has added subjects '''
        return self.cascaderAddedSubject(username, newSubjects)

    #--------

    def registerOnCascaderRemovedSubjects(self, func):
        self.cascaderRemovedSubject = func

    def remote_cascaderRemovedSubjects(self, username, removedSubjects):
        ''' Called when a cascader has removed some subjects '''
        return self.cascaderRemovedSubject(username, removedSubjects)

    #--------

    def remote_eval(self, code):
        raise NotImplementedError('Not going to happen')

    def remote_ping(self):
        return 'pong'
