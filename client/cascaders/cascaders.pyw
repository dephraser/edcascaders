'''
Startup file, responsible for setting up the application and starting the gui
'''

import logging

import gtk

from mainframe import CascadersFrame

import dbusutil
import dbus.service
import dbus.mainloop.glib

DEBUG = 1

class RaiseableService(dbusutil.DbusService):
    '''Service provides a method of raising the window to dbus'''
    def __init__(self, interface, path, app):
        super(RaiseableService, self).__init__(interface, path)
        self.app = app

    #FIXME can't seem to abstract this
    @dbus.service.method('com.compsoc')
    def showWindow(self):
        self.app.window.present()

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    if DEBUG:
        win = CascadersFrame()
        gtk.main()
    else:
        interface = 'com.compsoc'
        path = '/com/compsoc/cascaders'
        if not dbusutil.isOwner(interface):
            client = dbusutil.DbusClient(interface, path)
            client.showWindow()
        else:
            win = CascadersFrame()
            obj = RaiseableService(interface, path, win)
            gtk.main()
