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

class CascadersFrame(generatedgui.GenCascadersFrame):
    def __init__(self):
        generatedgui.GenCascadersFrame.__init__(self, None)
        self.client = None

        self.subjects  = []
        self.cascaders = []

        self.cascadeSubjects = set()

        self.cascading = False

        self.connect()

    #--------------------------------------------------------------------------
    # Connection stuff
    def isConnected(self):
        return self.client is not None

    def connect(self):
        ''' also does the setup post connect '''

        debug('Connecting...')
        self.mStatus.SetLabel('Connecting...')

        try:
            logname = os.environ['LOGNAME']
        except KeyError:
            msg = ('Couldn\'t get LOGNAME from the enviroment,'
                   ' this only runs on Linux at the moment')
            error(msg)
            #FIXME dialog box has ok cancel
            wx.MessageDialog(self,
                             msg,
                             'Error getting user name').ShowModal()
        self.mUserName.SetLabel(logname)

        try:
            self.client = client.RpcClient('localhost',
                                           5010,
                                           logname,
                                           socket.gethostname())
            self.client.getSubjectList(lambda s: (setattr(self, 'subjects', s.value), self.updateAllSubjects()))
            self.client.getCascaderList(lambda c: setattr(self, 'cascaders', c))
        except socket.error:
            msg = 'Failed to connect to server'
            error(msg)
            wx.MessageDialog(self,
                             msg,
                             'error connecting').ShowModal()
            self.Close()

        self.mStatus.SetLabel('Connected')

    #--------------------------------------------------------------------------
    def updateAllSubjects(self):
        debug('Subjects: %s' % self.subjects)
        self.mCascadeSubject.Clear()
        for subject in self.subjects:
            self.mCascadeSubject.Append(subject)

    def updateCascaderLists(self):
        pass

    #--------------------------------------------------------------------------
    def onStartStopCascading(self, event):
        if self.cascading:
            self.client.stopCascading()
        else:
            self.client.startCascading()
    
    def onAddSubject(self, event):
        subject = self.mCascadeSubject.GetStringSelection()
        if subject and not subject in self.cascadeSubjects:
            debug('Adding subject: %s' % subject)
            self.mCascadeSubjectList.Append(subject)
            self.client.addSubjects([subject])
            self.cascadeSubjects.add(subject)
    
    def onRemoveSubject(self, event):
        subject = self.mCascadeSubjectList.GetStringSelection()
        debug('Selected Subject is: %s' % subject)
        if subject and subject in self.cascadeSubjects:
            self.client.removeSubjects([subject])
            self.cascadeSubjects.remove(subject)

    # Filter Stuff
    def onSubjectSelect(self, event):
        self.updateCascaderLists()
    
    def onLabSelect(self, event):
        self.updateCascaderLists()
    #-- -----------------------------------------------------------------------
