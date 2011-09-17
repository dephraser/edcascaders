'''
This is the gui class for the main application frame and it handles most of the
core functionality that the user uses while using the application.

It doesn't handle any functionality outside the frame such as messaging
'''
from logging import warn, debug
import os
import sys
import socket

import gtk
import gtk.glade
import gobject

#rpc
import client
import service

from map import Locator
import map

#message boxes
from accepthelp import AcceptHelpDialog
from askdialog import AskForHelp
from messagedialog import MessageDialog

import util
from util import getComboBoxText, initTreeView, errorDialog

class Cascaders:
    ''' Manages the cascaders and provides helpful functions '''

    def __init__(self, locator, username):
        '''
        username is the current users username. This is excluded from
        results
        locator is a object that implements labFromHostname
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
            warn('Cascader that left didn\'t exist (maybe this user)')

    def removeCascaderSubjects(self, username, subjects):
        debug('Cascader %s removed subjects %s' % (username, subjects))
        try: 
            host, curSubjects = self.cascaders[username]
            for remSubject in subjects:
                try:
                    curSubjects.remove(remSubject)
                except ValueError:
                    debug('User wasn\'t cascading subject %s' % remSubject)
        except KeyError:
            warn('Tried to remove subjects from cascader %s, prob not cascading' % username)

    def findCascaders(self, lab=None, subjects=None, host=None):
        '''
        Find all cascaders that match the given patterns

        TODO really slow, not sure it matters
        '''
        for user, (cascHost, cascSubjects) in self.cascaders.iteritems():
            if host and host != cascHost:
                continue

            if lab and self.locator.labFromHostname(cascHost) != lab:
                continue

            if subjects and not subjects in cascSubjects:
                continue

            yield user, (host, cascSubjects)

    def findCascader(self, **kwargs):
        ''' Wrapper around findCascaders, returns the first match or None '''
        try:
            return self.findCascaders(**kwargs).next()
        except StopIteration:
            return None


class CascadersFrame:
    def __init__(self, debug=False):
        '''
        Enabling debug does things like disable async so errors are more 
        apparent
        '''
        self.debugEnabled = debug

        self.subjects  = [] #list of subjects, retrived from the server

        self.cascadeSubjects = set() #list of subjects the user is cascading in
        self.cascading = False #user cascading

        self.client = None #client for connection to server

        self.locator = Locator(open('./data/hosts'))
        self.username = self._getUsername()

        self.cascaders = Cascaders(self.locator, self.username) 

        self.initGui()

        self.trayIcon = gtk.status_icon_new_from_file('icons/cascade32.png')
        self.trayIcon.connect('activate', lambda *a: self.window.show_all())
        self.trayIcon.connect('popup-menu', self.onTrayMenu)
        self.window.connect('delete-event', lambda w, e: w.hide() or True)

        self.messageDialog = MessageDialog()

        self.map = map.Map(self.builder.get_object('tblMap'),
                           self.locator,
                           self.cascaders)

        self.initLabs()


        self.initService()

        self.initConnection()

    def initGui(self):
        self.builder = gtk.Builder()

        dr = os.path.dirname(__file__)
        self.builder.add_from_file(os.path.join(dr, 'gui', 'main.glade'))

        initTreeView(self.builder.get_object('tvCascList'))
        initTreeView(self.builder.get_object('tvCascSubjects'))

        self.window = self.builder.get_object('wnCascader')
        self.window.connect('destroy', lambda *a: gtk.main_quit())
        self.builder.connect_signals(self)

        self.window.show_all()

    def initLabs(self):
        '''
        Sets up the labs drop down box stuff
        '''
        if not hasattr(self, 'locator'):
            raise AttributeError('initLabs depends on self.locator')

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


    def _getUsername(self):
        try:
            logname = os.environ['LOGNAME']
            
            #for debugging only, means multiple clients can be run at once
            if self.debugEnabled:
                import random
                logname = str(random.random())
        except KeyError:
            errorDialog(('Couldn\'t get LOGNAME from the enviroment,'
                         ' this only runs on Linux at the moment'))
            #can't destroy the window as it leads to an exception
            sys.exit(1) 
        return logname

    #--------------------------------------------------------------------------
    # Connection stuff
    def initService(self):
        '''
        This sets up the service that the client provides to the server.

        This is required for setup
        '''

        s = self.service = service.RpcService()

        s.registerOnCascaderRemovedSubjects(self.onCascaderRemovedSubjects)
        s.registerOnCascaderAddedSubjects(self.onCascaderAddedSubjects)

        s.registerOnCascaderJoined(self.onCascaderJoined)
        s.registerOnCascaderLeft(self.onCascaderLeft)

        s.registerUserAskingForHelp(self.onUserAskingForHelp)


    def initConnection(self):
        ''' called in the constructor. also does the setup post connect '''

        debug('Connecting...')
        status = self.builder.get_object('lbStatus')
        status.set('Connecting...')



        self.hostname = socket.gethostname()
        self.builder.get_object('lbUsername').set(self.username)

        try:
            self.client = client.RpcClient(lambda b:self.service,
                                           'localhost',
                                           5010,
                                           self.username,
                                           self.hostname)

            if self.debugEnabled:
                self.client.setAsync(False)

            def subject(result):
                self.subjects = [x for x in result.value]
                self.updateAllSubjects()

            def casc(result):
                for usr, host, sub in result.value:
                    self.cascaders.addCascader(usr, host, sub)
                self.updateCascaderLists()

            self.client.getSubjectList(subject)
            self.client.getCascaderList(casc)
        except socket.error:
            errorDialog('Failed to connect to server')
            sys.exit(1)

        gobject.io_add_watch(self.client.conn, gobject.IO_IN, self.bgServer)
        status.set('Connected')

    def bgServer(self, source = None, cond = None):
        '''
        This function is called when there is data to be read in the pipe

        (It is setup in initConnection)
        '''
        if self.client.conn:
            self.client.conn.poll_all()
            return True
        else:
            return False
    #--------------------------------------------------------------------------
    # Service callback functions

    def onUserAskingForHelp(self,  helpid, username, subject, description):
        debug('Help wanted by: %s' % username)

        dialog = AcceptHelpDialog(username, subject, description)

        #check if user can give help
        if dialog.isAccept():
            debug('Help Accepted')

            self.messageDialog.addTab(helpid, username)

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
    def updateMap(self, lab):
        ''' Rebuilds the map '''
        self.map.applyFilter(lab)

    def updateAllSubjects(self):
        '''
        Calling this ensures that the gui reflects the current list of subjects
        '''
        debug('Subjects: %s' % self.subjects)

        cascCb = self.builder.get_object('cbCascSubjectList')
        lst = gtk.ListStore(gobject.TYPE_STRING)
        for s in self.subjects:
            lst.append([s])
        cascCb.set_model(lst)
        cell = gtk.CellRendererText()
        cascCb.set_active(0)
        cascCb.pack_start(cell, True)
        cascCb.add_attribute(cell, 'text', 0)

        cb = self.builder.get_object('cbFilterSubject')
        lst = gtk.ListStore(gobject.TYPE_STRING)
        lst.append(['All'])
        for s in self.subjects:
            lst.append([s])
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

        cascaders = self.cascaders.findCascaders(lab=filterLab, subjects=filterSub)
        for username, (hostname, subjects) in cascaders:
            ls.append([username])

    #--------------------------------------------------------------------------
    # GUI events
    def onStartStopCascading(self, event):
        btn = self.builder.get_object('btStartStopCasc')
        btn.set_sensitive(False)
        if self.cascading:
            debug('Stopping Cascading')
            self.cascading = False
            self.client.stopCascading(lambda *a: btn.set_sensitive(True))
            btn.set_label('Start Cascading')
        else:
            debug('Starting Cascading')
            self.cascading = True
            self.client.startCascading(lambda *a: btn.set_sensitive(True))
            btn.set_label('Stop Cascading')

    def onCascaderClick(self, tv, event):
        if event.button != 1 or event.type != gtk.gdk._2BUTTON_PRESS:
            return
        model, itr = tv.get_selection().get_selected()
        cascaderUsername = model.get_value(itr, 0)
        
        #ask user topic, brief description
        subject = None
        if getComboBoxText(self.builder.get_object('cbFilterSubject')) != 'All':
            subject = getComboBoxText(self.builder.get_object('cbFilterSubject'))
        helpDialog = AskForHelp(self, self.subjects, subject)

        if helpDialog.isOk():
            debug('Dialog is ok, asking for help')
            helpid = (self.username, util.generateUnqiueId())

            #add a tab
            self.messageDialog.addTab(helpid, cascaderUsername)

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
                accepted, message = result.value
                wf = self.messageDialog.writeMessage
                if accepted:
                    wf(helpid, 'SYSTEM', cascaderUsername + ' accepted your help request')
                else:
                    wf(helpid, 'SYSTEM', cascaderUsername + ' rejected your help request')
                    
                    if message:
                        wf(helpid, cascaderUsername, message)

            self.client.askForHelp(helpid,
                                   cascaderUsername,
                                   helpDialog.getSubject(),
                                   helpDialog.getDescription(),
                                   onResponse )
    
    def onAddSubject(self, event):
        cb = self.builder.get_object('cbCascSubjectList')
        ls = self.builder.get_object('lsCascSubjects')
        subject = getComboBoxText(cb)

        if subject and not subject in self.cascadeSubjects:
            debug('Adding subject: %s' % subject)

            ls.append([subject])
            self.client.addSubjects([subject])
            self.cascadeSubjects.add(subject)

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

    #-- -----------------------------------------------------------------------

    def onTrayMenu(self, icon, btn, time):
        '''
        Menu popup for the tray icon
        '''
        menu = gtk.Menu()

        quit = gtk.MenuItem()
        quit.set_label('Quit')
        quit.connect('activate', gtk.main_quit)
        menu.append(quit)

        menu.show_all()
        menu.popup(None,
                   None,
                   gtk.status_icon_position_menu,
                   btn,
                   time, self.trayIcon)
