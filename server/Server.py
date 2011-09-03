from __future__ import with_statement
from rpyc import Service, async
from rpyc.utils.server import ThreadedServer
from threading import RLock

broadcast_lock = RLock()
tokens = dict()

class UserToken(object):
    def __init__(self, user, hostname, callback):
        self.user = user
        self.hostname = hostname
        self.stale = False
        self.cascading = False
        self.subjects = []
        self.callback = callback
        tokens[user]=self
    
    def exposed_logout(self):
        if self.stale:
            return
        self.stale = True
        self.callback = None
        del tokens[self.user]
        
    def exposed_startCascading(self):
        #Add the user to active cascaders list
        self.cascading = True

    def exposed_stopCascading(self):
        #Remove the user from the active cascaders list
        self.cascading = False

    def exposed_addSubjects(subjects):
        #add the array of subjects to the users cascading list
        self.subjects.append(subjects)

    def exposed_removeSubjects(subjects):
        #remove the subjects from the users cascading list
        self

    def exposed_getCascaderList(self):
        #Return the list of cascaders and their subjects
        pass

    def exposed_getSubjectList(self):
        #Return the list of allowed subjects
        pass

    def exposed_askForHelp(helpId, username, subject, problem, self):
        #Ask the user specified in username for help
        pass

    def exposed_acceptHelp(helpId, self):
        #The cascader wants to help
        pass

    def exposed_rejectHelp(helpId, message, self):
        #The cascader doesn't want to help
        pass

    def exposed_sendMessage(helpId, toUser, message, self):
        #Send a message to the user
        pass

class ChatService(Service):
    
    #This is an automated method, it is not envoked by the coder
    def on_connect(self):
        self.token = None
    
    #This too is an automated method, it is not envoked by the coder
    def on_disconnect(self):
        if self.token:
            self.token.exposed_logout()
    
    def exposed_userJoin(self, username, hostname, callback):
        if self.token and not self.token.stale:
            raise ValueError("already logged in")
        else:
            self.token = UserToken(username, async(callback))
            return self.token


if __name__ == "__main__":
    t = ThreadedServer(ChatService, port = 5010)
    print("Spinning the server up, stand by")
    t.start()
