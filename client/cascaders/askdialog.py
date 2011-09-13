import os

import gtk
import gobject

from util import getComboBoxText, errorDialog

class AskForHelp:
    '''
    Core functionality for the ask for help box, includes validation
    '''
    def __init__(self, parent, subjects, currentSubject = None):
        '''
        subjects - List of all subjects
        currentSubject - The subject that should be selected by default
        '''
        self.builder = gtk.Builder()
        dr = os.path.dirname(__file__)
        self.builder.add_from_file(os.path.join(dr, 'gui', 'askforhelp.glade'))

        self.window = self.builder.get_object('dgAskForHelp')
        self.builder.connect_signals(self)

        self.window.show_all()

        cb = self.builder.get_object('cbSubject')
        ls = gtk.ListStore(gobject.TYPE_STRING)
        cb.set_model(ls)
        for i,subject in enumerate(subjects):
            ls.append([subject])
            if subject == currentSubject:
                cb.set_active(i)

        cell = gtk.CellRendererText()
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)

        self.subject = self.desc = None
        self.ok = False

        self.window.run()

    def onCancel(self, event):
        self.window.destroy()

    def onOk(self, event):
        #need to get these before everything is destroyed
        self.subject = getComboBoxText(self.builder.get_object('cbSubject'))
        self.desc = self.builder.get_object('txDesc').get_text()

        if not len(self.getDescription().strip()):
            errorDialog('There must be a problem description')
        elif self.getSubject() is None:
            errorDialog('Must have a subject selected')

        self.ok = True
        self.window.destroy()

    #--------------------------------------------------------------------------
    # Functions designed for external use

    def isOk(self):
        ''' Did the user press Ok? '''
        return self.ok

    def getSubject(self):
        return self.subject

    def getDescription(self):
        return self.desc
