import dbus
import dbus.service

class DbusService(dbus.service.Object):
    ''' Provides an program api to allow other programs to communicate '''

    def __init__(self, interface, path):
        self.interface = interface
        busName = dbus.service.BusName(interface, bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, busName, path)


class DbusClient(object):
    def __init__(self, interface, path):
        self.obj = dbus.SessionBus().get_object(interface, path)

    def __getattribute__(self, name):
        if name == 'obj':
            return object.__getattribute__(self, name)
        return getattr(self.obj, name)

def isOwner(interface):
    return dbus.SessionBus().request_name(interface) == dbus.bus.REQUEST_NAME_REPLY_PRIMARY_OWNER

