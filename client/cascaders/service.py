import rpyc

class RpcService(rpyc.Service):
    '''
    This provides the service for data sent from the server to the client
    '''

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
        pass

    def exposed_helpResponse(self, helpid, accepted, response=None):
        '''
        This isn't needed if the response from the cascaders userAskingForHelp
        can be returned to the user -> server askForHelp call.

        Otherwise this is called when from Server to User with the response
        from the cascader to the request from help
        '''
        pass

    def exposed_eval(self, code):
        raise NotImplementedError('Not going to happen')
