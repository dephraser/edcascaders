'''
This is the gui class for the main application frame and it handles most of the
core functionality that the user uses while using the application.

It doesn't handle any functionality outside the frame such as messaging
'''
from logging import debug, error
import os
import sys
import socket

import gtk
import gtk.glade
import gobject

import client
import service
from locator import Locator
from askdialog import AskForHelp

from util import getComboBoxText, initTreeView, errorDialog

DEBUG = True

import time
def generateUnqiueId():
    return str(time.time())

class CascadersFrame:
    def onTrayMenu(self, icon, btn, time):
        menu = gtk.Menu()

        quit = gtk.MenuItem()
        quit.set_label('Quit')
        quit.connect('activate', gtk.main_quit)
        menu.append(quit)

        menu.show_all()
        menu.popup(None, None, gtk.status_icon_position_menu, btn, time, self.trayIcon)


    def __init__(self):
        self.initGui()
        self.trayIcon = gtk.status_icon_new_from_file('icons/cascade32.png')
        self.trayIcon.connect('activate', lambda *a: self.window.show_all())
        self.window.connect('delete-event', lambda w, e: w.hide() or True)
        self.trayIcon.connect('popup-menu', self.onTrayMenu)

        self.client = None

        self.subjects  = []
        self.cascaders = []

        self.cascadeSubjects = set()

        self.cascading = False

        self.locator = Locator(open('./data/hosts'))

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

        self.initService()
        self.initConnection()

    def initGui(self):
        self.builder = gtk.Builder()
        self.root = self.builder.add_from_file('gui/main.glade')

        initTreeView(self.builder.get_object('tvCascList'))
        initTreeView(self.builder.get_object('tvCascSubjects'))

        self.window = self.builder.get_object('wnCascader')
        self.window.connect('destroy', lambda *a: gtk.main_quit())
        self.builder.connect_signals(self)

        self.window.show_all()


    def initService(self):
        s = self.service = service.RpcService()

        #s.registerOnCascaderRemovedSubjects
        #s.registerOnCascaderAddedSubjects

        #s.registerOnCascaderJoined
        #s.registerOnCascaderLeft

        #s.registerUserAskingForHelp

    #--------------------------------------------------------------------------
    # Connection stuff

    def initConnection(self):
        ''' called in the constructor. also does the setup post connect '''

        debug('Connecting...')
        status = self.builder.get_object('lbStatus')
        status.set('Connecting...')

        try:
            logname = os.environ['LOGNAME']
            
            #for debugging only, means multiple clients can be run at once
            if DEBUG:
                import random
                logname = str(random.random())
        except KeyError:
            errorDialog(('Couldn\'t get LOGNAME from the enviroment,'
                         ' this only runs on Linux at the moment'))
            #can't destroy the window as it leads to an exception
            sys.exit(1) 
        self.logname = logname
        self.builder.get_object('lbUsername').set(logname)

        try:
            self.client = client.RpcClient(lambda b:self.service,
                                           'localhost',
                                           5010,
                                           logname,
                                           socket.gethostname())

            self.client.getSubjectList(lambda s: (setattr(self, 'subjects', s.value), self.updateAllSubjects()))
            self.client.getCascaderList(lambda c: (setattr(self, 'cascaders', c.value), self.updateCascaderLists()))
        except socket.error:
            errorDialog('Failed to connect to server')
            sys.exit(1)

        gobject.io_add_watch(self.client.conn, gobject.IO_IN, self.bgServer)
        status.set('Connected')

    def bgServer(self, source = None, cond = None):
        if self.client.conn:
            self.client.conn.poll_all()
            return True
        else:
            return False
    #--------------------------------------------------------------------------
    def updateAllSubjects(self):
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
        debug('Cascaders: %s' % [u for u, h, s in self.cascaders])

        ls = self.builder.get_object('lsCascList')
        ls.clear()

        cbSubjects = self.builder.get_object('cbFilterSubject')
        cbLabs = self.builder.get_object('cbFilterLab')
        for username, hostname, subjects in self.cascaders:
            lab = self.locator.labFromHostname(hostname)

            filterSub = getComboBoxText(cbSubjects)
            if filterSub in subjects or filterSub == 'All':
                if getComboBoxText(cbLabs) in ['All', lab]:
                    ls.append([username])


    #--------------------------------------------------------------------------
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
            helpid = (self.logname, generateUnqiueId())
            self.client.askForHelp(helpid,
                                   cascaderUsername,
                                   helpDialog.getSubject(),
                                   helpDialog.getDescription())
    
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
