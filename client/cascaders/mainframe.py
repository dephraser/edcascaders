'''
This is the gui class for the main application frame and it handles most of the
core functionality that the user uses while using the application.

It doesn't handle any functionality outside the frame such as messaging
'''
from logging import error, warn, debug
import os
import sys
import socket
import signal

import gtk
import gobject

from twisted.internet import reactor
import twisted.internet.error

#rpc
import client, service

import labmap
import settings

from requirements import RequireFunctions

#message boxes
from accepthelp import AcceptHelpDialog
from askdialog import AskForHelp
from messagedialog import MessageDialog

from trayicon import TrayIcon

import util
from util import getComboBoxText, initTreeView, errorDialog


class Cascaders:
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
        if username != self.username:
            self.cascaders[username] = (host, list(subjects))

    def removeCascader(self, username):
        try:
            del self.cascaders[username]
        except KeyError:
            warn('Cascader that left didn\'t exist (maybe this user)')

    def addCascaderSubjects(self, username, subjects):
        try:
            host, curSubjects = self.cascaders[username]
            self.cascaders[username] = (host, curSubjects + list(subjects))
        except KeyError:
            warn('Cascader (%s) that added subjects '
                 'didn\'t exist (maybe this user)' % username)

    def removeCascaderSubjects(self, username, subjects):
        debug('Cascader %s removed subjects %s' % (username, subjects))
        try: 
            curSubjects = self.cascaders[username][1]
            for remSubject in subjects:
                try:
                    curSubjects.remove(remSubject)
                except ValueError:
                    debug('User wasn\'t cascading subject %s' % remSubject)
        except KeyError:
            warn('Tried to remove subjects from cascader %s, '
                 'prob not cascading or this user' % username)

    def findCascaders(self, lab=None, subjects=None, host=None):
        '''
        Find all cascaders that match the given patterns, although
        this will not return any cascaders that are not cascading in 
        any subjects

        TODO really slow, not sure it matters
        '''
        for user, (cascHost, cascSubjects) in self.cascaders.iteritems():
            if len(cascSubjects) == 0:
                continue

            if host and host != cascHost:
                continue

            if lab and self.locator.labFromHostname(cascHost) != lab:
                continue

            if (subjects and
                    len(set(subjects).intersection(set(cascSubjects))) == 0):
                continue

            yield user, (host, cascSubjects)

    def findCascader(self, username=None, **kwargs):
        ''' Wrapper around findCascaders, returns the first match or None '''
        if username is not None:
            if len(kwargs):
                error('Username not supported with other args')
                return None
            try:
                host, subjects = self.cascaders[username]
                if len(subjects) == 0:
                    return None
                return username, (host, subjects)
            except KeyError:
                warn('Couldn\'t find cascader with username: ' % username)
                return None

        try:
            return self.findCascaders(**kwargs).next()
        except StopIteration:
            return None
 
#-------------------------------------------------------------------------------
#constants
PORT = 5010
HOST = 'kazila.jacobessex.com'
#-------------------------------------------------------------------------------

class CascadersFrame:
    def __init__(self, debugEnabled=False, show=True, host=None):
        '''
        Enabling debug does things like disable async so errors are more 
        apparent

        show should be true to show the windows by default
        '''
        self.debugEnabled = debugEnabled

        self.subjects  = [] #list of subjects, retrived from the server

        self.cascadeSubjects = set() #list of subjects the user is cascading in
        self.cascading = False #user cascading

        self.client = None #client for connection to server

        hosts = os.path.join(os.path.dirname(__file__), 'data', 'hosts')
        self.locator = labmap.Locator(open(hosts))
        self.username = self._getUsername()

        self.cascaders = Cascaders(self.locator, self.username) 

        self.messageDialog = MessageDialog(self.locator, self.cascaders)

        if host is None:
            self.hostname = socket.gethostname().lower()
        else:
            self.hostname = host

        #slightly more sane method of setting things up that uses depency
        #tracking
        req = RequireFunctions()
        req.add('gui', self.initGui)
        req.add('tray', self.initTray, ['gui'])
        req.add('map', self.initMap, ['gui'])
        req.add('labs', self.initLabs, ['map'])
        req.add('service', self.initService)
        req.add('connection', self.initConnection, ['service'])
        req.add('signals', self.initSignals, ['gui', 'settings'])
        req.add('settings', self.initSettings, ['gui', 'connection'])
        req.run()

        if show:
            self.window.show_all()

        if self.settings['asked_autostart'] == False:
            self.settings['asked_autostart'] = True
            message = gtk.MessageDialog(None,
                                        gtk.DIALOG_MODAL,
                                        gtk.MESSAGE_INFO,
                                        gtk.BUTTONS_YES_NO,
                                        ('Do you want to autostart this '
                                         'program on login?'))
            resp = message.run()
            if resp == gtk.RESPONSE_YES:
                self.builder.get_object('cbAutostart').set_active(True)
            message.destroy()

    def initMap(self):
        self.map = labmap.Map(self.builder.get_object('tblMap'),
                              self.locator,
                              self.cascaders)

    def initTray(self):
        icon = os.path.join(os.path.dirname(__file__),
                            'icons',
                            'cascade32.png')
        self.trayIcon = TrayIcon(self, icon)
        self.window.connect('delete-event', lambda w, e: w.hide() or True)

    def initSignals(self):
        ''' Signals catch events and shut things down properly '''
        signal.signal(signal.SIGINT, self.quit)
        signal.signal(signal.SIGTERM, self.quit)

    def initGui(self):
        self.builder = gtk.Builder()

        dr = os.path.dirname(__file__)
        self.builder.add_from_file(os.path.join(dr, 'gui', 'main.glade'))

        initTreeView(self.builder.get_object('tvCascList'))
        initTreeView(self.builder.get_object('tvCascSubjects'))

        self.window = self.builder.get_object('wnCascader')
        self.window.connect('destroy', lambda *a: gtk.main_quit())
        self.builder.connect_signals(self)

    def initLabs(self):
        ''' Sets up the labs drop down box stuff '''
        lst = gtk.ListStore(gobject.TYPE_STRING)
        lst.append(['All'])
        for lab in self.locator.getLabs():
            lst.append([lab])
        cb = self.builder.get_object('cbFilterLab')
        cb.set_model(lst)
        cell = gtk.CellRendererText()
        cb.set_active(0)
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)

    def initSettings(self):
        self.settings = settings.loadSettings()

        autostart = self.settings['autostart']
        self.builder.get_object('cbAutostart').set_active(autostart)
        autocascade = self.settings['autocascade']
        self.builder.get_object('cbAutocascade').set_active(autocascade)

        self.addSubjects(self.settings['cascSubjects'])

        if self.settings['cascading'] and self.settings['autocascade']:
            self.startCascading()

    def _getUsername(self):
        try:
            logname = os.environ['LOGNAME']
            
            #for debugging only, means multiple clients can be run at once
            if self.debugEnabled == True:
                import random
                logname = str(random.random())
        except KeyError:
            errorDialog(('Couldn\'t get LOGNAME from the enviroment,'
                         ' this only runs on Linux at the moment'))
            self.quit()
        return logname

    def initService(self):
        '''
        This sets up the service that the client provides to the server.
        '''
        s = self.service = service.RpcService()

        s.registerOnCascaderRemovedSubjects(self.onCascaderRemovedSubjects)
        s.registerOnCascaderAddedSubjects(self.onCascaderAddedSubjects)

        s.registerOnCascaderJoined(self.onCascaderJoined)
        s.registerOnCascaderLeft(self.onCascaderLeft)

        s.registerUserAskingForHelp(self.onUserAskingForHelp)

    def initConnection(self):
        '''
        called in the constructor. also does the setup post connect
        '''
        debug('Connecting...')
        status = self.builder.get_object('lbStatus')
        status.set('Connecting...')

        self.builder.get_object('lbUsername').set(self.username)

        self.client = client.RpcClient(self.service,
                                       HOST,
                                       PORT,
                                       self.username,
                                       self.hostname)

        def subject(result):
            self.subjects = [x for x in result]
            self.updateAllSubjects()

        def casc(result):
            for usr, host, sub in result:
                self.cascaders.addCascader(usr, host, sub)
            self.updateCascaderLists()

        #nb: these functions are not called until login
        self.client.getSubjectList().addCallback(subject)
        self.client.getCascaderList().addCallback(casc)
        self.client.registerLoginCallback(lambda *a: status.set('Connected'))

        #error "handling"
        def loginErr(reason):
            reason = reason.trap(ValueError)
            errorDialog('Failed to login, server reported %s' % reason.getErrorMessage())
            self.quit()

        def connectErr(reason):
            reason.trap(twisted.internet.error.ConnectionRefusedError)
            errorDialog('Failed to connect to the '
                        'server, the connection was refused')
            self.quit()

        self.client.registerLoginErrCallback(loginErr)
        self.client.registerConnectErrCallback(connectErr)

    #--------------------------------------------------------------------------
    # Service callback functions, most of these are just simple wrappers
    # around the cascaders class.

    def onUserAskingForHelp(self,  helpid, username, host,
                            subject, description):
        debug('Help wanted by: %s with host %s' % (username, host))

        dialog = AcceptHelpDialog(self.window, username, subject, description)

        #check if user can give help
        if dialog.isAccept():
            debug('Help Accepted')

            print 'Ok, host is %s' % host
            self.messageDialog.addTab(helpid, username,
                                      self.hostname, host, True)

            #setup functions to write to the messages from the message dialog to
            #the server
            f = lambda msg: self.messageDialog.writeMessage(helpid, username, msg)
            self.service.registerOnMessgeHandler(helpid, f)

            #functions to write from server to message window
            wf =  lambda msg: self.client.sendMessage(helpid, username, subject, msg)
            self.messageDialog.registerMessageCallback(helpid, wf)

            self.messageDialog.writeMessage(helpid, 'SYSTEM', 'Accepted Request')
            self.messageDialog.window.show_all()

            return (True, '')

        debug('Help rejected')
        return (False, '')

    def onCascaderAddedSubjects(self, username, subjects):
        debug('Cascader %s added subjects %s' % (username, subjects))
        self.cascaders.addCascaderSubjects(username, subjects)
        self.updateCascaderLists()

    def onCascaderRemovedSubjects(self, username, subjects):
        debug('Cascader %s removed subjects %s' % (username, subjects))
        self.cascaders.removeCascaderSubjects(username, subjects)
        self.updateCascaderLists()

    def onCascaderJoined(self, username, hostname, subjects):
        debug('New cascader: %s' % username)
        self.cascaders.addCascader(username, hostname, subjects)
        self.updateCascaderLists()

    def onCascaderLeft(self, username):
        debug('Cascader left: %s' % username)
        self.cascaders.removeCascader(username)
        self.updateCascaderLists()

    #--------------------------------------------------------------------------
    def updateAllSubjects(self):
        '''
        Calling this ensures that the gui reflects the current list of subjects
        '''
        debug('Subjects: %s' % self.subjects)

        cascCb = self.builder.get_object('cbCascSubjectList')
        lst = gtk.ListStore(gobject.TYPE_STRING)
        [lst.append([subject]) for subject in self.subjects]
        cascCb.set_model(lst)
        cell = gtk.CellRendererText()
        cascCb.set_active(0)
        cascCb.pack_start(cell, True)
        cascCb.add_attribute(cell, 'text', 0)

        cb = self.builder.get_object('cbFilterSubject')
        lst = gtk.ListStore(gobject.TYPE_STRING)
        lst.append(['All'])
        [lst.append([subject]) for subject in self.subjects]
        cb.set_model(lst)
        cell = gtk.CellRendererText()
        cb.set_active(0)
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)

    def updateCascaderLists(self):
        '''
        Cleans the list and updates the list of cascaders avaible. Call
        when filters have been changed
        '''
        debug('Cascaders: %s' % self.cascaders)

        ls = self.builder.get_object('lsCascList')
        ls.clear()

        cbSubjects = self.builder.get_object('cbFilterSubject')
        filterSub = getComboBoxText(cbSubjects)
        filterSub = [filterSub] if filterSub != 'All'  else None

        cbLab = self.builder.get_object('cbFilterLab')
        filterLab = getComboBoxText(cbLab)
        filterLab = filterLab if filterLab != 'All' else None

        cascaders = self.cascaders.findCascaders(lab=filterLab,
                                                 subjects=filterSub)
        [ls.append([username]) for username, _ in cascaders]

    #--------------------------------------------------------------------------
    # GUI events
    def quit(self, *a):
        '''
        This quits the application, doing the required shutdown stuff. If some
        thing goes in here, try to assume nothing about the state of the
        application.
        '''
        debug('Starting shutdown')

        if self.settings:
            self.settings['cascSubjects'] = list(self.cascadeSubjects)
            self.settings['cascading'] = self.cascading
            self.settings['autostart'] = self.builder.get_object('cbAutostart').get_active()
            self.settings['autocascade'] = self.builder.get_object('cbAutocascade').get_active()

        #quit the gui to try and make everything look snappy (so we don't lock
        #when messing around doing IO. we can't use destory else other 
        #things don't work
        if self.window:
            self.window.hide_all() 

        if self.client is not None:
            debug('Logging out')
            try:
                gobject.timeout_add(5000, self._finishQuitTimeout)
                l = self.client.logout()
                l.addCallback(self._finishQuit)
                l.addErrCallback(self._finishQuitErr)
            except Exception:
                self._finishQuit()
        else:
            debug('No client, going to second stage shutdown directly')
            self._finishQuit()

    def _finishQuitTimeout(self):
        debug('Logging out timed out')
        self._finishQuit()
        return False #we should return false here due to using timeout_add

    def _finishQuitErr(self, reason):
        debug('There was an error logging out %s' % str(reason))
        self._finishQuit()

    def _finishQuit(self, result=None):
        debug('In second stage shutdown')
        if self.window:
            self.window.destroy()

        #seems to be a bug, but we need to clean up the threadpool
        if reactor.threadpool is not None:
            reactor.threadpool.stop()
        try:
            reactor.stop()
        except twisted.internet.error.ReactorNotRunning:
            debug('Reactor wasn\'t running, so couldn\'t stop it')

        if self.settings:
            settings.saveSettings(self.settings)

        debug('Finished shutdown, goodbye')

    def onStartStopCascading(self, event):
        ''' Toggles cascading '''
        btn = self.builder.get_object('btStartStopCasc')
        btn.set_sensitive(False)
        if self.cascading:
            debug('Stopping Cascading')
            self.stopCascading()
        else:
            debug('Starting Cascading')
            self.startCascading()

    def stopCascading(self):
        btn = self.builder.get_object('btStartStopCasc')
        self.cascading = False
        self.client.stopCascading().addCallback(lambda *a: btn.set_sensitive(True))
        btn.set_label('Start Cascading')

    def startCascading(self):
        btn = self.builder.get_object('btStartStopCasc')
        if len(self.cascadeSubjects) == 0:
            errorDialog('You cannot start cascading when you no subjects')
            btn.set_sensitive(True)
        else:
            #we offer the user to automatically start cascading
            askedAutoCascading = self.settings['asked_autocascade']
            autoCascade = self.settings['autocascade'] == False
            if askedAutoCascading == False and autoCascade:
                self.settings['asked_autocascade'] = True

                message = gtk.MessageDialog(None,
                                            gtk.DIALOG_MODAL,
                                            gtk.MESSAGE_INFO,
                                            gtk.BUTTONS_YES_NO,
                                            "Do you want to enable auto cascading")
                resp = message.run()
                if resp == gtk.RESPONSE_YES:
                    self.builder.get_object('cbAutocascade').set_active(True)
                message.destroy()


            self.cascading = True
            self.client.startCascading().addCallback(lambda *a: btn.set_sensitive(True))
            btn.set_label('Stop Cascading')

    def onCascaderClick(self, tv, event):
        if event.button != 1 or event.type != gtk.gdk._2BUTTON_PRESS:
            return
        model, itr = tv.get_selection().get_selected()
        cascaderUsername = model.get_value(itr, 0)
        self.askForHelp(cascaderUsername)

    def askForHelp(self, cascaderUsername):
        (_, (cascHost, cascSubjects)) = self.cascaders.findCascader(username=cascaderUsername)

        print 'Cascader host is %s' % cascHost
        
        #ask user topic, brief description
        subject = None
        if getComboBoxText(self.builder.get_object('cbFilterSubject')) != 'All':
            subject = getComboBoxText(self.builder.get_object('cbFilterSubject'))
        helpDialog = AskForHelp(self.window, cascSubjects, subject)

        if helpDialog.isOk():
            debug('Dialog is ok, asking for help')
            helpid = (self.username, util.generateUnqiueId())

            #add a tab
            self.messageDialog.addTab(helpid, cascaderUsername, self.hostname,
                                      cascHost, False)

            #setup functions to write to the message stuff when messages
            #come from the server to the client
            f = lambda msg: self.messageDialog.writeMessage(helpid, cascaderUsername, msg)
            self.service.registerOnMessgeHandler(helpid, f)

            #setup handler to send messages from the dialog to the server
            wf =  lambda msg: self.client.sendMessage(helpid, cascaderUsername, subject, msg)
            self.messageDialog.registerMessageCallback(helpid, wf)

            self.messageDialog.writeMessage(helpid, 'SYSTEM', 'Wating for response')
            self.messageDialog.window.show_all()

            def onResponse(result):
                ''' Response from asking for help '''
                accepted, message = result
                wf = self.messageDialog.writeMessage
                if accepted:
                    wf(helpid,
                       'SYSTEM',
                       cascaderUsername + ' accepted your help request')
                else:
                    wf(helpid,
                       'SYSTEM',
                       cascaderUsername + ' rejected your help request')
                    
                    if message:
                        wf(helpid, cascaderUsername, message)

            d = self.client.askForHelp(helpid,
                                       cascaderUsername,
                                       helpDialog.getSubject(),
                                       helpDialog.getDescription())
            d.addCallback(onResponse)

    
    def onAddSubject(self, event):
        cb = self.builder.get_object('cbCascSubjectList')
        self.addSubjects([getComboBoxText(cb)])

    def addSubjects(self, subjects):
        ls = self.builder.get_object('lsCascSubjects')
        for subject in subjects:
            if subject and not subject in self.cascadeSubjects:
                debug('Adding subject: %s' % subject)

                ls.append([subject])
                self.cascadeSubjects.add(subject)

        self.client.addSubjects(subjects)
        debug('Subjects now: %s' % self.cascadeSubjects)

    
    def onRemoveSubject(self, event):
        tv = self.builder.get_object('tvCascSubjects')
        model, itr = tv.get_selection().get_selected()
        subject = model.get_value(itr, 0)

        if subject and subject in self.cascadeSubjects:
            debug('Removing subject: %s' % subject)
            self.client.removeSubjects([subject])
            self.cascadeSubjects.remove(subject)

            model.remove(itr)
        debug('Subjects now: %s' % self.cascadeSubjects)

        if len(self.cascadeSubjects) == 0 and self.cascading:
            debug('No more subjects and we are cascading')
            self.stopCascading()


    # Filter Stuff
    def onSubjectSelect(self, event):
        self.updateCascaderLists()
    
    def onLabSelect(self, event):
        self.updateCascaderLists()

    #-- -----------------------------------------------------------------------

    def onFilterLabChange(self, evt):
        '''
        This is called before a lot of the things are created fully
        as it is set to its default value. This has to check that things
        fully exist before calling functions on them
        '''
        debug('Filter Lab Changed')

        self.updateCascaderLists()

        cbLab = self.builder.get_object('cbFilterLab')
        lab = getComboBoxText(cbLab)
        self.updateMap(lab)

    def onFilterSubjectChange(self, evt):
        debug('Filter Subject Changed')
        self.updateCascaderLists()

    def updateMap(self, lab):
        cbSubjects = self.builder.get_object('cbFilterSubject')
        filterSub = getComboBoxText(cbSubjects)
        filterSub = [filterSub] if filterSub != 'All'  else None

        def onHostClick(event, widgit, host):
            casc = self.cascaders.findCascader(host=host, subjects=filterSub)
            if casc is None:
                debug('Clicked on a host (%s) that wasn\'t '
                      'cascading for the given filter' % host)
                return
            (username, _) = casc
            self.askForHelp(username)

        self.map.applyFilter(lab,
                             myHost=self.hostname,
                             subjects=filterSub,
                             onClick=onHostClick)
