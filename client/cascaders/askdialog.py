'''
Functionality for the Ask for Help dialog
'''

import generatedgui

class AskForHelp(generatedgui.GenAskForHelp):
    '''
    Core functionality for the ask for help box, this is designed to be shown
    with ShowModal rather than show
    '''
    def __init__(self, parent, subjects, currentSubject = None):
        '''
        subjects - List of all subjects
        currentSubject - The subject that should be selected by default
        '''
        generatedgui.GenAskForHelp.__init__(self, parent)
        self.ok = False

        self.mSubject.Clear()
        for subject in subjects:
            self.mSubject.Append(subject)

        if currentSubject:
            index = self.mSubject.FindString(currentSubject)
            self.mSubject.SetSelection(index)

    def onCancel(self, event):
        self.Close()

    def onOk(self, event):
        if not self.isValid():
            #TODO
            pass
        else:
            self.ok = True
            self.Close()

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
        return self.mSubject.GetStringSelection()

    def getDescription(self):
        return self.mDescription.GetValue()
