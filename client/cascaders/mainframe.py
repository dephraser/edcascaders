'''
This is the gui class for the main application frame and it handles most of the
core functionality that the user uses while using the application.

It doesn't handle any functionality outside the frame such as messaging
'''
from logging import debug, error
import os
import socket

import wx

import generatedgui
import client
from locator import Locator
from askdialog import AskForHelp

def errorDialog(title, msg):
        error('%s - %s' % (title, msg))
        wx.MessageDialog(None,
                         msg,
                         title,
                         style=wx.OK|wx.ICON_ERROR).ShowModal()

class CascadersFrame(generatedgui.GenCascadersFrame):
    def __init__(self):
        generatedgui.GenCascadersFrame.__init__(self, None)
        self.client = None

        self.subjects  = []
        self.cascaders = []

        self.cascadeSubjects = set()

        self.cascading = False

        self.locator = Locator(open('./data/hosts'))

        self.mFilterLab.Clear()
        self.mFilterLab.Append('All')
        for lab in self.locator.getLabs():
            self.mFilterLab.Append(lab)
        self.mFilterLab.SetSelection(0)

        self.mFilteredCascaderList.Append('yacoby')

        self.connect()

    #--------------------------------------------------------------------------
    # Connection stuff

    def connect(self):
        ''' called in the constructor. also does the setup post connect '''

        debug('Connecting...')
        self.mStatus.SetLabel('Connecting...')

        try:
            logname = os.environ['LOGNAME']
        except KeyError:
            errorDialog('Couldn\'t get user name',
                          ('Couldn\'t get LOGNAME from the enviroment,'
                           ' this only runs on Linux at the moment'))
        self.mUserName.SetLabel(logname)

        try:
            self.client = client.RpcClient('localhost',
                                           5010,
                                           logname,
                                           socket.gethostname())
            self.client.getSubjectList(lambda s: (setattr(self, 'subjects', s.value), self.updateAllSubjects()))
            self.client.getCascaderList(lambda c: (setattr(self, 'cascaders', c.value), self.updateCascaderLists()))
        except socket.error:
            errorDialog('Error Connecting', 'Failed to connect to server')
            self.Close()

        self.mStatus.SetLabel('Connected')

    #--------------------------------------------------------------------------
    def updateAllSubjects(self):
        debug('Subjects: %s' % self.subjects)
        self.mCascadeSubject.Clear()
        for subject in self.subjects:
            self.mCascadeSubject.Append(subject)

        self.mFilterSubject.Clear()
        self.mFilterSubject.Append('All')
        for subject in self.subjects:
            self.mFilterSubject.Append(subject)
        self.mFilterSubject.SetSelection(0)

    def updateCascaderLists(self):
        '''
        Cleans the list and updates the list of cascaders avaible. Call
        when filters have been changed
        '''
        self.mFilteredCascaderList.Clear()

        for username, hostname, subjects in self.cascaders:
            lab = self.locator.getLabFromHostname(hostname)

            if (self.mFilterSubjects.GetSelection() == 0 or
                    self.mFilterSubjects.GetStringSelection() in subjects):

                if (self.mFilterLab.GetSelection() == 0 or
                        self.mFilterLab.GetStringSelection() == lab ):
                    self.mFilteredCascaderList.Append(username)

    #--------------------------------------------------------------------------
    def onStartStopCascading(self, event):
        self.mCascadeStartStop.Disable()
        if self.cascading:
            self.cascading = False
            self.client.stopCascading(lambda: self.mCascadeStartStop.Enable())
            self.mCascadeStartStop.SetLabel('Start Cascading')
        else:
            self.cascading = True
            self.client.startCascading(lambda: self.mCascadeStartStop.Enable())
            self.mCascadeStartStop.SetLabel('Stop Cascading')

    def onCascaderDClick(self, event):
        cascaderUsername = event.GetString()
        
        #ask user topic, brief description
        subject = None
        if self.mFilterSubject.GetSelection() != 0:
            subject = self.mFilterSubject.GetSelection()
        helpDialog = AskForHelp(self, self.subjects, subject)
        helpDialog.ShowModal()

        if helpDialog.isOk():
            helpid = 1 #FIXME
            self.client.askForHelp(helpId,
                                   cascaderUsername,
                                   helpDialog.getSubject(),
                                   helpDialog.getDescription())
    
    def onAddSubject(self, event):
        subject = self.mCascadeSubject.GetStringSelection()
        if subject and not subject in self.cascadeSubjects:
            debug('Adding subject: %s' % subject)
            self.mCascadeSubjectList.Append(subject)
            self.client.addSubjects([subject])
            self.cascadeSubjects.add(subject)
        debug('Subjects now: %s' % self.cascadeSubjects)
    
    def onRemoveSubject(self, event):
        subject = self.mCascadeSubjectList.GetStringSelection()
        if subject and subject in self.cascadeSubjects:
            debug('Removing subject: %s' % subject)
            self.client.removeSubjects([subject])
            self.cascadeSubjects.remove(subject)
            index = self.mCascadeSubjectList.FindString(subject)
            self.mCascadeSubjectList.Delete(index)
        debug('Subjects now: %s' % self.cascadeSubjects)

    # Filter Stuff
    def onSubjectSelect(self, event):
        self.updateCascaderLists()
    
    def onLabSelect(self, event):
        self.updateCascaderLists()
    #-- -----------------------------------------------------------------------
