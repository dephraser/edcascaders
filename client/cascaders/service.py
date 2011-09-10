import rpyc

class RpcService(rpyc.Service):
    '''
    This provides the service for data sent from the server to the client
    '''
    def __init__(self):
        self.messageFunctions = {}
        self.userAskingForHelp = None

        self.cascaderJoined = None
        self.cascaderLeft = None

        self.cascaderAddedSubject = None
        self.cascaderRemovedSubject = None
    #---------------------------------------------------------------------------

    def registerUserAskingForHelp(self, func):
        self.userAskingForHelp = func

    def exposed_userAskingForHelp(self, helpId, username, subject, description):
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
        self.userAskingForHelp()

    #--------

    def registerOnMessgeHandler(self, helpid, func):
        self.messageFunctions[helpid] = func

    def exposed_userSentMessage(self, helpid, message):
        try:
            self.messageFunctions[helpid](message)
        except KeyError:
            pass

    #--------
    
    def registerOnCascaderJoined(self, func):
        self.cascaderJoined = func

    def exposed_cascaderJoined(self, username, hostname, subjects):
        ''' Called when a cascader starts cascading '''
        self.cascaderJoined()

    #--------

    def registerOnCascaderLeft(self, func):
        self.cascaderLeft = func

    def exposed_cascaderLeft(self, username):
        ''' Called when a cascader stops cascading '''
        self.cascaderLeft()

    #--------

    def registerOnCascaderAddedSubjects(self, func):
        self.cascaderAddedSubject = func

    def exposed_cascaderAddedSubjects(self, username, newSubjects):
        ''' Called when a cascader has added subjects '''
        self.cascaderAddedSubject()

    #--------

    def registerOnCascaderRemovedSubjects(self, func):
        self.cascaderRemovedSubject = func

    def exposed_cascaderRemovedSubjects(self, username, removedSubjects):
        ''' Called when a cascader has removed some subjects '''
        self.cascaderRemovedSubject()

    #--------

    def exposed_eval(self, code):
        raise NotImplementedError('Not going to happen')
