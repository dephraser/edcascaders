'''
Functionality for the Ask for Help dialog
'''

import generatedgui

class AskForHelp(generatedgui.GenAskForHelp):
    def __init__(self, parent, subjects, currentSubject = None):
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
        self.ok = True
        self.Close()

    def isOk(self):
        return self.ok

    def getSubject(self):
        return self.mSubject.GetStringSelection()

    def getDescription(self):
        return self.mDescription.GetValue()
