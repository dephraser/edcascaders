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

from cascadermodel import CascaderModel

from requirements import RequireFunctions

#message boxes
from accepthelp import AcceptHelpDialog
from askdialog import AskForHelp
from messagedialog import MessageDialog

from trayicon import TrayIcon

import util
from util import getComboBoxText, initTreeView, errorDialog

#-------------------------------------------------------------------------------
class CascadersFrame:
    def __init__(self, debugEnabled=False, show=True, host=None):
        '''
        Enabling debug does things like disable async so errors are more 
        apparent

        show should be true to show the windows by default
        '''
        self.debugEnabled = debugEnabled


        hosts = os.path.join(os.path.dirname(__file__), 'data', 'hosts')
        self.locator = labmap.Locator(open(hosts))
        self.username = self._getUsername()


        if host is None:
            self.hostname = socket.gethostname().lower()
        else:
            self.hostname = host

        self.model = CascaderModel(self.locator, self.username, self.hostname)
        self.messageDialog = MessageDialog(self.locator, self.model.getCascaderData())

        #slightly more sane method of setting things up that uses depency
        #tracking
        req = RequireFunctions()
        req.add('gui', self.initGui)
        req.add('tray', self.initTray, ['gui'])
        req.add('map', self.initMap, ['gui'])
        req.add('labs', self.initLabs, ['map'])
        req.add('modelcallbacks', self.initModelCallbacks)
        req.add('connection', self.initConnection)
        req.add('signals', self.initSignals, ['gui', 'settings'])
        req.add('settings', self.initSettings, ['gui', 'connection'])
        req.add('autostart', self.askAutostart, ['gui', 'settings'])
        req.run()

        if show:
            self.window.show_all()

    def askAutostart(self):
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
                              self.model.getCascaderData())

    def initTray(self):
        icon = os.path.join(os.path.dirname(__file__),
                            'icons',
                            'cascade.ico')
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

        debug('Got subjects from settings: %s' % str(self.settings['cascSubjects']))

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

    def initModelCallbacks(self):
        '''
        This sets up the service callbacks
        '''
        self.model.registerOnCascaderChanged(self.updateCascaderLists)
        self.model.registerOnSubjectChanged(self.updateAllSubjects)
        self.model.registerOnUserAskingForHelp(self.onUserAskingForHelp)

        self.model.registerOnDisconnected(self.onDisconnect)
        self.model.registerOnConnected(self.onLogin)

    def onDisconnect(self):
        status = self.builder.get_object('lbStatus')
        status.set('Connecting...')

    def onLogin(self):
        status = self.builder.get_object('lbStatus')
        status.set('Connected')

    def initConnection(self):
        '''
        called in the constructor. also does the setup post connect
        '''
        debug('Connecting...')
        self.builder.get_object('lbUsername').set(self.username)

        def loginErr(reason):
            reason = reason.trap(ValueError)
            errorDialog('Failed to login, server reported %s' % reason.getErrorMessage())
            self.quit()

        def connectErr(reason):
            reason.trap(twisted.internet.error.ConnectionRefusedError)
            errorDialog('Failed to connect to the '
                        'server, the connection was refused')
            self.quit()

        def connected(result):
            d = self.model.login()
            d.addErrback(loginErr)

        d = self.model.connect()
        d.addCallback(connected)
        d.addErrback(connectErr)

    #--------------------------------------------------------------------------
    def setupMessagingWindow(self, helpid, toUsername, remoteHost, isUserCasc):
        '''
        toUsername - the username of the remote
        remoteHost - the hostname of the remote
        '''
        self.messageDialog.addTab(helpid, toUsername,
                                  self.hostname, remoteHost, isUserCasc)

        #setup functions to write to the messages from the message dialog to
        #the server
        def onMessageFromServer(fromType, message):
            if fromType == 'user':
                fromName = toUsername 
            elif fromType == 'server':
                fromName = 'Server'
            self.messageDialog.writeMessage(helpid, self.username, message)
            
        self.model.registerOnMessgeHandler(helpid, onMessageFromServer)

        def writeFunction(message):
            try:
                self.model.sendMessage(helpid, toUsername, message)
            except client.NotConnected:
                self.onServerLost()

        self.messageDialog.registerMessageCallback(helpid, writeFunction)

        self.messageDialog.window.show_all()

    #--------------------------------------------------------------------------
    # Service callback functions, most of these are just simple wrappers
    # around the cascaders class.

    def onUserAskingForHelp(self,  helpid, username, host,
                            subject, description):
        '''
        Called from the server to the client cascader to see if help can
        be accepted
        '''
        debug('Help wanted by: %s with host %s' % (username, host))

        dialog = AcceptHelpDialog(self.window, username, subject, description)

        #check if user can give help
        if dialog.isAccept():
            debug('Help Accepted')
            self.setupMessagingWindow(helpid, username, host, True)
            return (True, '')

        debug('Help rejected')
        return (False, '')


    #--------------------------------------------------------------------------
    def updateAllSubjects(self, subjects):
        '''
        Calling this ensures that the gui reflects the current list of subjects
        '''
        debug('Subjects: %s' % subjects)

        cascCb = self.builder.get_object('cbCascSubjectList')
        lst = gtk.ListStore(gobject.TYPE_STRING)
        [lst.append([subject]) for subject in subjects]
        cascCb.set_model(lst)
        cell = gtk.CellRendererText()
        cascCb.set_active(0)
        cascCb.pack_start(cell, True)
        cascCb.add_attribute(cell, 'text', 0)

        cb = self.builder.get_object('cbFilterSubject')
        lst = gtk.ListStore(gobject.TYPE_STRING)
        lst.append(['All'])
        [lst.append([subject]) for subject in subjects]
        cb.set_model(lst)
        cell = gtk.CellRendererText()
        cb.set_active(0)
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)

    def updateCascaderLists(self, cascaders):
        '''
        Cleans the list and updates the list of cascaders avaible. Call
        when filters have been changed
        '''

        ls = self.builder.get_object('lsCascList')
        ls.clear()

        cbSubjects = self.builder.get_object('cbFilterSubject')
        filterSub = getComboBoxText(cbSubjects)
        filterSub = [filterSub] if filterSub != 'All'  else None

        cbLab = self.builder.get_object('cbFilterLab')
        filterLab = getComboBoxText(cbLab)
        filterLab = filterLab if filterLab != 'All' else None

        cascaders = list(cascaders.findCascaders(lab=filterLab,
                                                 subjects=filterSub))
        [ls.append([username]) for username, _ in cascaders]
        debug('Updating cascaders from: %s' % str(cascaders))

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
            debug('Updating Settings')
            self.settings['cascSubjects'] = list(self.model.cascadingSubjects())
            self.settings['cascading'] = self.model.isCascading()
            self.settings['autostart'] = self.builder.get_object('cbAutostart').get_active()
            self.settings['autocascade'] = self.builder.get_object('cbAutocascade').get_active()

        #quit the gui to try and make everything look snappy (so we don't lock
        #when messing around doing IO. we can't use destory else other 
        #things don't work
        if self.window:
            self.window.hide_all() 

        if self.model is not None:
            debug('Logging out')
            try:
                gobject.timeout_add(5000, self._finishQuitTimeout)
                l = self.model.logout()
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
        if self.model.isCascading():
            debug('Stopping Cascading')
            self.stopCascading()
        else:
            debug('Starting Cascading')
            self.startCascading()

    def stopCascading(self):
        btn = self.builder.get_object('btStartStopCasc')
        self.model.stopCascading().addCallback(lambda *a: btn.set_sensitive(True))
        btn.set_label('Start Cascading')

    def startCascading(self):
        btn = self.builder.get_object('btStartStopCasc')

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


        self.model.startCascading().addCallback(lambda *a: btn.set_sensitive(True))
        btn.set_label('Stop Cascading')

    def onCascaderClick(self, tv, event):
        if event.button != 1 or event.type != gtk.gdk._2BUTTON_PRESS:
            return
        model, itr = tv.get_selection().get_selected()
        if itr:
            cascaderUsername = model.get_value(itr, 0)
            self.askForHelp(cascaderUsername)

    def askForHelp(self, cascaderUsername):
        (_, (cascHost, cascSubjects)) = self.model.getCascaderData().findCascader(username=cascaderUsername)

        #ask user topic, brief description
        subject = None
        if getComboBoxText(self.builder.get_object('cbFilterSubject')) != 'All':
            subject = getComboBoxText(self.builder.get_object('cbFilterSubject'))
        helpDialog = AskForHelp(self.window, cascSubjects, subject)

        if helpDialog.isOk():
            debug('Dialog is ok, asking for help')
            helpid = (self.username, util.generateUnqiueId())

            self.setupMessagingWindow(helpid, cascaderUsername, cascHost, False) 

            self.messageDialog.writeMessage(helpid,
                                            'SYSTEM',
                                            'Wating for response')

            try:
                d = self.model.askForHelp(helpid,
                                          cascaderUsername,
                                          helpDialog.getSubject(),
                                          helpDialog.getDescription())
            except client.NotConnected:
                self.onServerLost()
    
    def onAddSubject(self, event):
        cb = self.builder.get_object('cbCascSubjectList')
        self.addSubjects([getComboBoxText(cb)])

    def addSubjects(self, subjects):
        ls = self.builder.get_object('lsCascSubjects')
        for subject in subjects:
            if subject not in self.model.cascadeSubjects:
                debug('Adding subject: %s' % subject)
                ls.append([subject])

        self.model.addSubjects(subjects)
    
    def onRemoveSubject(self, event):
        tv = self.builder.get_object('tvCascSubjects')
        model, itr = tv.get_selection().get_selected()
        if itr is not None:
            subject = model.get_value(itr, 0)
            model.remove(itr)
            self.model.removeSubjects([subject])

    # Filter Stuff
    def onSubjectSelect(self, event):
        self.updateCascaderLists(self.model.getCascaderData())
    
    def onLabSelect(self, event):
        self.updateCascaderLists(self.model.getCascaderData())

    #-- -----------------------------------------------------------------------

    def onFilterLabChange(self, evt):
        '''
        This is called before a lot of the things are created fully
        as it is set to its default value. This has to check that things
        fully exist before calling functions on them
        '''
        debug('Filter Lab Changed')

        self.updateCascaderLists(self.model.getCascaderData())

        cbLab = self.builder.get_object('cbFilterLab')
        lab = getComboBoxText(cbLab)
        self.updateMap(lab)

    def onFilterSubjectChange(self, evt):
        debug('Filter Subject Changed')
        self.updateCascaderLists(self.model.getCascaderData())

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
