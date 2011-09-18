import os
import gtk

from logging import debug

class AcceptHelpDialog():
    ''' Dialog asking the user if they will accept helping the user '''
    def __init__(self, parentWindow, username, subject, description):
        builder = gtk.Builder()

        dr = os.path.dirname(__file__)
        builder.add_from_file(os.path.join(dr, 'gui', 'helpacceptreject.glade'))

        self.window = builder.get_object('dgHelpAcceptReject')
        if parentWindow is not None:
            self.window.set_transient_for(parentWindow)
        builder.get_object('lbUserInfo').set_label('%s is wanting help on %s' % (username, subject))
        builder.get_object('lbDesc').set_label(description)
        builder.connect_signals(self)

        self.accept = True

        self.window.show_all()
        self.window.run()

    def onReject(self, e):
        self.accept = False
        self.window.destroy()

    def onAccept(self, e):
        debug('Cascader accepted')
        self.accept = True
        self.window.destroy()

    #--------------------------------------------------------------------------
    # Functions for external use

    def isAccept(self):
        return self.accept


