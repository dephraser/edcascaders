import os

import gtk
import gobject

from util import getComboBoxText

class AskForHelp:
    '''
    Core functionality for the ask for help box
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

        self.ok = False

        self.window.run()

    def onCancel(self, event):
        self.window.destroy()

    def onOk(self, event):
        if not self.isValid():
            #TODO
            pass
        else:
            self.ok = True
            self.window.destroy()

    def isValid(self):
        '''
        This validates the user input to check that all is as it should
        be. Basically that there is a problem description entered,
        and a subject is selected
        '''
        #TODO
        return True

    #--------------------------------------------------------------------------
    # Functions designed for external use

    def isOk(self):
        ''' Did the user press Ok? '''
        return self.ok

    def getSubject(self):
        return getComboBoxText(self.builder.get_object('cbSubject'))

    def getDescription(self):
        return self.builder.get_object('txDesc').get_text()
