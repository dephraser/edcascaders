
import gtk
import gobject

class TrayIcon:
    def __init__(self, cascWindow, icon):
        self.casc = cascWindow 
        self.trayIcon = gtk.status_icon_new_from_file(icon)
        self.trayIcon.connect('activate', self._onTrayClick)
        self.trayIcon.connect('popup-menu', self._onTrayMenu)

    def _onTrayMenu(self, icon, btn, time):
        '''
        Menu popup for the tray icon
        '''
        menu = gtk.Menu()

        quitItem = gtk.MenuItem()
        quitItem.set_label('Quit')
        quitItem.connect('activate', self.casc.quit)
        menu.append(quitItem)

        menu.show_all()
        menu.popup(None,
                   None,
                   gtk.status_icon_position_menu,
                   btn,
                   time, self.trayIcon)

    def _onTrayClick(self, *args):
        ''' Shows the main window '''
        self.flashTray(0)
        self.casc.window.show_all()
        self.casc.window.present()

    def flashTray(self, timeout):
        if timeout == 0:
            self.trayIcon.set_blinking(False)
        else:
            self.trayIcon.set_blinking(True)
            gobject.timeout_add(timeout, lambda *a: self.trayIcon.set_blinking(False))
