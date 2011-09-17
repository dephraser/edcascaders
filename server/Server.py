from __future__ import with_statement
from rpyc import Service 
from rpyc.utils.server import ThreadedServer
from threading import RLock

import logging
import logging.handlers

LOG_FILENAME = 'cascader.log'


logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)


handler = logging.handlers.TimedRotatingFileHandler( LOG_FILENAME, when='W6', interval=1, backupCount=0, encoding=None, delay=False, utc=False)

formmatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

handler.setFormatter(formmatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())



data_lock = RLock()

tokens = dict()


subjectList = ["inf1-fp","inf1-cl","inf1-da","inf1-op","inf2a","inf2b","inf2c-cs",
        "inf2-se","inf2d","Java","Haskell","Python","Ruby","C","C++","PHP",
        "JavaScript", "Perl", "SQL", "Bash", "Vim", "Emacs", "Eclipse", "Netbeans",
        "Version Control"]

class UserToken(object):
    def __init__(self, conn, user, hostname):
        self.conn = conn
        self.user = user
        self.hostname = hostname
        self.stale = False
        self.cascading = False
        self.subjects = []
        tokens[user]=self
    
    def exposed_logout(self):
        '''
        Automatically called when the client disconnects

        Cleans up after itself and will remove the information from the local lists
        '''
        logging.info(self.user + "left")
        if self.stale:
            return
        self.stale = True

        del tokens[self.user] 

        #Need to inform other clients 
        with data_lock:
            for value in tokens.itervalues():
                #This is a remote produre call to the clients
                value.conn.root.cascaderLeft(self.user)
        

        
    def exposed_startCascading(self):
        '''
        Called by the client when the user wants to start cascading

        It will also envoke cascaderJoined in all the clients connected to let them
        know that the user has started cascading and to update their local lists
        '''

        self.cascading = True
        logger.info(self.user + " is going to start cascading")
        with data_lock:
            #Need to inform all other clients that this cascader has joined
            for value in tokens.itervalues():
                #This a remote procedure call to the client
                value.conn.root.cascaderJoined(self.user, self.hostname, \
                        self.subjects)
        logger.info(self.user + " has started cascading")

    def exposed_stopCascading(self):
        '''
        Call by the client when the user wants to stop cascading

        It will also envoke cascaderLeft on all of the clients connected to let 
        them know to update their local lists
        '''

        self.cascading = False
        with data_lock:
            for value in tokens.itervalues():
                value.conn.root.cascaderLeft(self.user)
        logger.info(self.user + " has stopped cascading")

    def exposed_addSubjects(self, subjects):
        '''
        Called by the client when the user adds some subjects to their collections

        It will also envoke casscaderAddedSubjects on all clients connected to 
        notify them and so they can update their local lists
        '''

        with data_lock:
            self.subjects.extend(subjects)
            if self.cascading:
                for value in tokens.itervalues():
                    value.conn.root.cascaderAddedSubjects(self.user, subjects)
        logger.info(self.user + " added " + str(list(subjects)) + " to their subject list")

    def exposed_removeSubjects(self, subjects):
        '''
        Called by the client when the user removes some subjects from their 
        collection

        It will also envoke cascaderRemovedSubjects on all clients connected to 
        notify them and so they can update their local lists
        '''

        with data_lock:
            for subject in subjects:
                self.subjects.remove(subject)
            for value in tokens.itervalues():
                value.conn.root.cascaderRemovedSubjects(self.user, subjects)
        logger.info(self.user + " removed " + subjects + " from their list")

    def exposed_getCascaderList(self):
        '''
        Called by the client requesting a list of the current cascaders operating
        with their usernames, hostnames and the subjects they are cascading on.

        Will return a list of 3 item tuples, each with the username and hostname as
        string and the list of subjects as a list
        '''

        with data_lock:
            returnvalue = [(value.user, value.hostname, value.subjects)
                            for value in tokens.itervalues() if value.cascading]
        logger.info(self.user + " asked for the cascader list")
        return returnvalue
    
    def exposed_getSubjectList(self):
        '''
        Called by the client requesting a list of the current subjects that can 
        be cascaded

        Will return as a list
        '''

        logger.info(self.user + " asked for the subject list")
        return subjectList

    def exposed_askForHelp(self, helpId, username, subject, problem):
        '''
        Called when the client is asking another user for help

        This will call a function on the client that the user who the help is being
        requested from (userAskingForHelp) and return the result of this function 
        to the user who called it in the first place

        The helpId variable is generated by the client and should just be passed on
        '''

        logger.info(self.user + " asked " + username + " for help on " + problem + \
                " in the subject " + subject)
        return tokens[username].conn.root.userAskingForHelp(helpId, self.user, \
                self.hostname, subject, problem) 

    def exposed_sendMessage(self, helpId, toUser, message):
        '''
        Called when the client is wanting to send a message to another client

        This will call a local function on the clients instance on the server
        which will send the message down

        HelpId is generated by the client and should just be passed on
        '''

        tokens[toUser].message(helpId, message)

    def message(self, helpId, message):
        '''
        Called when some other client on the server wants to send a message to 
        the client respective to this object

        Calls a function on the client connected

        helpID is generated by the client and should just be passed on
        '''

        self.conn.root.userSentMessage(helpId, message)
    
    def exposed_eval(self, code):
        raise NotImplementedError('In your dreams')

class ChatService(Service):
    
    #This is an automated method, it is not envoked by the coder
    def on_connect(self):
        self.token = None
    
    #This too is an automated method, it is not envoked by the coder
    def on_disconnect(self):
        if self.token:
            self.token.exposed_logout()
    
    def exposed_userJoin(self, username, hostname):
        if self.token and not self.token.stale:
            raise ValueError("already logged in")
        else:
            self.token = UserToken(self._conn, username, hostname)
            return self.token


if __name__ == "__main__":
    t = ThreadedServer(ChatService, port = 5010)
    logger.info("Spinning the server up, stand by")
    t.start()
