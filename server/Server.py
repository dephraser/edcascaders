from __future__ import with_statement

from twisted.spread import pb
from twisted.internet import reactor

from threading import RLock

import logging
import logging.handlers

#------------------------------------------------------------------------------
# logging

LOG_FILENAME = 'cascader.log'

logger = logging.getLogger('MyLogger')
logger.setLevel(logging.DEBUG)

handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME,
                                                    when='W6',
                                                    interval=1,
                                                    backupCount=0,
                                                    encoding=None) 
                                                    #Don't work with python 2.6
                                                    #, delay=False, utc=False)

formmatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

handler.setFormatter(formmatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())

#------------------------------------------------------------------------------
# constants
subjectList = set(["inf1-fp","inf1-cl","inf1-da","inf1-op","inf2a","inf2b","inf2c-cs",
        "inf2-se","inf2d","Java","Haskell","Python","Ruby","C","C++","PHP",
        "JavaScript", "Perl", "SQL", "Bash", "Vim", "Emacs", "Eclipse", "Netbeans",
        "Version Control"])



#maybe not needed. CPython isn't threaded
data_lock = RLock()

#global dict of users that are currently logged in
users = {}


class UserService(pb.Referenceable):
    def __init__(self, client, user, hostname):
        self.client = client 
        self.user = user
        self.hostname = hostname
        self.stale = False
        self.cascading = False
        self.subjects = set()
        users[user] = self

        self.startPingClientLoop()

    def startPingClientLoop(self):
        '''
        This ensures that cascaders who are not connected are removed from 
        the system
        '''
        try:
            self.client.callRemote('ping')
        except pb.DeadReferenceError:
            self.user.remote_logout()
        reactor.callLater(120, self.startPingClientLoop)
    
    def remote_logout(self):
        '''
        Automatically called when the client disconnects

        Cleans up after itself and will remove the information from the local lists
        '''
        logging.info(self.user + "left")
        if self.stale:
            return
        self.stale = True

        del users[self.user] 

        #Need to inform other clients 
        with data_lock:
            for user in users.itervalues():
                try:
                    if user.cascading:
                        user.client.callRemote('cascaderLeft', self.user)
                    user.client.callRemote('userLeft', self.user)
                except pb.DeadReferenceError:
                    logger.debug('Client wasn\'t connected')
                    user.remote_logout()

    def remote_startCascading(self):
        '''
        Called by the client when the user wants to start cascading

        It will also envoke cascaderJoined in all the clients connected to let them
        know that the user has started cascading and to update their local lists
        '''

        self.cascading = True
        logger.info(self.user + " is going to start cascading")
        with data_lock:
            #Need to inform all other clients that this cascader has joined
            for user in users.itervalues():
                #This a remote procedure call to the client
                try:
                    user.client.callRemote('cascaderJoined', self.user,
                                            self.hostname, self.subjects)
                except pb.DeadReferenceError:
                    logger.debug('Client wasn\'t connected')
                    user.remote_logout()

        logger.info(self.user + " has started cascading")

    def remote_stopCascading(self):
        '''
        Call by the client when the user wants to stop cascading

        It will also envoke cascaderLeft on all of the clients connected to let 
        them know to update their local lists
        '''

        self.cascading = False
        with data_lock:
            for user in users.itervalues():
                try:
                    user.client.callRemote('cascaderLeft', self.user)
                except pb.DeadReferenceError:
                    logger.debug('Client wasn\'t connected')
                    user.remote_logout()

        logger.info(self.user + " has stopped cascading")

    def remote_addSubjects(self, subjects):
        '''
        Called by the client when the user adds some subjects to their collections

        It will also envoke casscaderAddedSubjects on all clients connected to 
        notify them and so they can update their local lists
        '''

        #strip out things not listed in the valid subjects
        subjects = set(subjects).intersection(subjectList)

        with data_lock:
            self.subjects.update(subjects)
            if self.cascading:
                for user in users.itervalues():
                    try:
                        user.client.callRemote('cascaderAddedSubjects', self.user, subjects)
                    except pb.DeadReferenceError:
                        logger.debug('Client wasn\'t connected')
                        user.remote_logout()

        logger.info(self.user + " added " + str(list(subjects)) + " to their subject list")

    def remote_removeSubjects(self, subjects):
        '''
        Called by the client when the user removes some subjects from their 
        collection

        It will also envoke cascaderRemovedSubjects on all clients connected to 
        notify them and so they can update their local lists
        '''
        subjects = set(subjects).intersection(subjectList)

        with data_lock:
            for subject in subjects:
                try:
                    self.subjects.remove(subject)
                except KeyError:
                    #item wasn't in set, ignore
                    logger.warn('Tried to remove %s from subjects, failed' % subject)

            for user in users.itervalues():
                try:
                    user.client.callRemote('cascaderRemovedSubjects', self.user, subjects)
                except pb.DeadReferenceError:
                    logger.debug('Client wasn\'t connected')
                    user.remote_logout()

        logger.info(self.user + " removed " + str(list(subjects)) + " from their list")

    def remote_getCascaderList(self):
        '''
        Called by the client requesting a list of the current cascaders operating
        with their usernames, hostnames and the subjects they are cascading on.

        Will return a list of 3 item tuples, each with the username and hostname as
        string and the list of subjects as a list
        '''

        with data_lock:
            returnvalue = [(value.user, value.hostname, value.subjects)
                            for value in users.itervalues() if value.cascading]
        logger.info(self.user + " asked for the cascader list")
        return returnvalue
    
    def remote_getSubjectList(self):
        '''
        Called by the client requesting a list of the current subjects that can 
        be cascaded

        Will return as a list
        '''

        logger.info(self.user + " asked for the subject list")
        return subjectList

    def remote_askForHelp(self, helpId, username, subject, problem):
        '''
        Called when the client is asking another user for help

        This will call a function on the client that the user who the help is being
        requested from (userAskingForHelp) and return the result of this function 
        to the user who called it in the first place

        The helpId variable is generated by the client and should just be passed on
        '''

        logger.info(self.user + " asked " + username + " for help on " + problem + \
                " in the subject " + subject)
        try:
            deferred = users[username].client.callRemote('userAskingForHelp',
                                                          helpId, self.user,
                                                          self.hostname,
                                                          subject, problem) 
        except pb.DeadReferenceError:
            logger.debug('Client wasn\'t connected')
            users[username].remote_logout()

        cb = lambda res : self.onAskForHelpResponse(helpId, username, res)
        deferred.addCallback(cb)
        return deferred 

    def onAskForHelpResponse(self, helpId, cascUsername, result):
        '''
        Deals with logging from the cascaders response for asking for hlp
        '''
        (answer,why) = result

        if answer:
            logger.info(cascUsername + "said yes, help is now being given")

            msg = cascUsername + ' accepted your help request' 
            self.client.callRemote('serverSentMessage', helpId, msg)

            messages = ['Remember to use pastebin to show code',
                        ('It may be easier to ask for a cascader to come to '
                         'your desk so you can explain the problem in person')]
            for m in messages:
                self.client.callRemote('serverSentMessage', helpId, m)
        else:
            logger.info(cascUsername + "said no: " + why)

            msg = cascUsername + ' rejected your help request' 
            self.client.callRemote('serverSentMessage', helpId, msg)

    def remote_sendMessage(self, helpId, toUser, message):
        '''
        Called when the client is wanting to send a message to another client

        This will call a local function on the clients instance on the server
        which will send the message down

        HelpId is generated by the client and should just be passed on
        '''

        try:
            users[toUser].message(helpId, message)
        except pb.DeadReferenceError:
            logger.debug('Client wasn\'t connected')
            self.remote_logout()

        logger.info(self.user + "->" + toUser + ":" + message)

    def message(self, helpId, message):
        '''
        Called when some other client on the server wants to send a message to 
        the client respective to this object

        Calls a function on the client connected

        helpID is generated by the client and should just be passed on
        '''

        try:
            self.client.callRemote('userSentMessage', helpId, message)
        except pb.DeadReferenceError:
            logger.debug('Client wasn\'t connected')
            self.remote_logout()

    def remote_ping(self):
        ''' Can be used to see that the server is up and functioning '''
        return 'pong'
    
    def remote_eval(self, code):
        raise NotImplementedError('In your dreams')


class LoginService(pb.Root):
    ''' 
    Provides a service that requires the user to login before being able
    to access other methods. This reduces the amount of checks required
    in the UserService class
    '''
    def remote_userJoin(self, client, username, hostname):
        if username in users:
            raise ValueError("Username in use")
        else:
            return UserService(client, username, hostname)

if __name__ == "__main__":
    reactor.listenTCP(5010, pb.PBServerFactory(LoginService()))
    logger.info("Spinning the server up, stand by")
    reactor.run()
