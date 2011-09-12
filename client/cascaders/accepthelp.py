import gtk

class AcceptHelpDialog():
    def __init__(self, username, subject, description):
        self.builder = gtk.Builder()
        self.root = self.builder.add_from_file('gui/helpacceptreject.glade')

        self.window = self.builder.get_object('dgHelpAcceptReject')
        self.builder.get_object('lbUserInfo').set_label('%s is wanting help on %s' % (username, subject))
        self.builder.get_object('lbDesc').set_label(description)
        self.builder.connect_signals(self)

        self.isAccept = True

        self.window.show_all()
        self.window.run()


    def onAccept(self, e):
        self.isAccept = True
        self.window.destroy()

    def onReject(self, e):
        self.window.destroy()

    def isAccept(self):
        return self.isAccept


