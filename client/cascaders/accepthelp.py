import os
import gtk

class AcceptHelpDialog():
    ''' Dialog asking the user if they will accept helping the user '''
    def __init__(self, username, subject, description):
        builder = gtk.Builder()

        dr = os.path.dirname(__file__)
        builder.add_from_file(os.path.join(dr, 'gui', 'helpacceptreject.glade'))

        self.window = builder.get_object('dgHelpAcceptReject')
        builder.get_object('lbUserInfo').set_label('%s is wanting help on %s' % (username, subject))
        builder.get_object('lbDesc').set_label(description)
        builder.connect_signals(self)

        self.accept = True

        self.window.show_all()
        self.window.run()

    def onReject(self, e):
        self.window.destroy()

    def onAccept(self, e):
        self.accept = True
        self.window.destroy()

    #--------------------------------------------------------------------------
    # Functions for external use

    def isAccept(self):
        return self.accept


