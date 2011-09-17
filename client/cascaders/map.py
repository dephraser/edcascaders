from logging import warn

import ConfigParser as configparser
from collections import defaultdict

import gtk

class Locator():
    '''
    This class is responsbile for providing location information based on hostname
    as well as being able to provide map data
    '''

    def _parseLocation(self, location):
        x,y = location.split(',')
        return int(x.strip()),  int(y.strip())

    def __init__(self, fileHandle):
        self.hosts = configparser.ConfigParser()
        self.hosts.readfp(fileHandle)

        self.labs = defaultdict(list)
        self.hostsLab = {}
        for lab in self.hosts.sections():
            for hostname, v in self.hosts.items(lab):
                hostname += '.inf.ed.ac.uk'
                self.hostsLab[hostname] = lab
                self.labs[lab].append((hostname, self._parseLocation(v)))

    def getLabs(self):
        return self.hosts.sections()

    def labFromHostname(self,hostname):
        try:
            return self.hostsLab[hostname]
        except KeyError:
            return None

    def getMap(self, lab):
        try:
            return self.labs[lab]
        except KeyError:
            warn('No map info for %s: ' % lab)
            return []

    def hasMap(self, lab):
        return lab in self.labs

    def getMapBounds(self, lab):
        try: 
            mx = max([x for h, (x,y) in self.getMap(lab)])
            my = max([y for h, (x,y) in self.getMap(lab)])
            return mx, my
        except ValueError:
            warn('No host info for %s: ' % lab)
            return 0,0


class Map:
    '''
    Wrapper around a gtk grid that provides an interface as a map
    '''
    def __init__(self, widget, locator):
        self.widget = widget
        self.locator = locator

    def setNoMap(self):
        self.widget.resize(1,1)
        l = gtk.Label()
        l.set_text('No map')
        l.show_all()
        self.widget.attach(l, 0,1,0,1)

    def applyFilter(self, lab, subjects=None):
        '''
        Redraws the map with the given filters applied
        '''
        [x.destroy() for x in self.widget.get_children()]

        if not self.locator.hasMap(lab):
            return self.setNoMap()

        mx,my = self.locator.getMapBounds(lab)
        self.widget.resize(mx,my)

        for host, (x,y) in self.locator.getMap(lab):
            labelText = host.split('.')[0]

            #if hosts and host == self.hostname:
            #    labelText += '\n<color="red">You Are Here</color>'
            #else:
            #    cascader = self.cascaders.findCascader(host=host)
            #    if cascader is not None:
            #        labelText += '\n<color="blue">Cascading: [%s]</color>' % cascader[1]

            x = mx - x
            l = gtk.Label()
            l.set_markup(labelText)
            l.show_all()
            self.widget.attach(l, x,x+1,y,y+1)
