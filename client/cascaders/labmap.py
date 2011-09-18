'''
File has classes to manage map and location data.
'''
from logging import warn

import ConfigParser as configparser
from collections import defaultdict

import gtk

class Locator():
    '''
    This class is responsbile for providing location information based on hostname
    as well as being able to provide map data. Internally this uses configparser
    to deal with the data which is a list of key, value with the key 
    being the host and the value being the location
    '''

    def _parseLocation(self, location):
        '''
        Fairly relaxed configuration parser for the location string
        '''
        x, y = location.split(',')
        return int(x.strip()),  int(y.strip())

    def __init__(self, fileHandle):
        ''' 
        fileHandle - a file like object that holds the data
        '''
        self.hosts = configparser.ConfigParser()
        self.hosts.readfp(fileHandle)

        self.labs = defaultdict(list)
        self.hostsLab = {}
        for lab in self.hosts.sections():
            for hostname, v in self.hosts.items(lab):
                self.hostsLab[hostname] = lab
                self.labs[lab].append((hostname, self._parseLocation(v)))

    def getLabs(self):
        return self.hosts.sections()

    def labFromHostname(self, hostname):
        try:
            return self.hostsLab[hostname]
        except KeyError:
            return None

    def getMap(self, lab):
        ''' A map is a list of: (host, (xpos, ypos)) '''
        try:
            return self.labs[lab]
        except KeyError:
            warn('No map info for %s: ' % lab)
            return []

    def hasMap(self, lab):
        return lab in self.labs

    def getMapBounds(self, lab):
        '''
        Returns a tuple of the maximum x,y bounds of the map. The minimum
        is assumed to be 0,0 as (at present) this is how the data is setup
        '''
        try: 
            mx = max([x for h, (x, y) in self.getMap(lab)])
            my = max([y for h, (x, y) in self.getMap(lab)])
            return mx, my
        except ValueError:
            warn('No host info for %s: ' % lab)
            return 0, 0


class Map:
    '''
    Wrapper around a gtk table that provides an interface as a map with
    data from the location class
    '''
    def __init__(self, widget, locator, cascaders):
        self.widget = widget
        self.locator = locator
        self.cascaders = cascaders

    def setNoMap(self):
        self.widget.resize(1, 1)
        l = gtk.Label()
        l.set_text('No map')
        l.show_all()
        self.widget.attach(l, 0, 1, 0, 1)

    def _shouldHighlightCascader(self, host, hosts, subjects):
        cascader = self.cascaders.findCascader(host=host)
        if not cascader:
            return False

        username, (host, cascSubjects) = cascader
        if hosts and host not in hosts:
            return False

        if subjects and len(set(cascSubjects).intersection(set(subjects))) == 0:
            return False

        return True

    def applyFilter(self, lab, myHost=None, cascaderHosts=None,
                    helpedHosts=None, subjects=None, onClick=None):
        '''
        Redraws the map with the given filters applied, so that only the 
        cascaders that match the parameters are highlighted
        '''
        [x.destroy() for x in self.widget.get_children()]

        if not self.locator.hasMap(lab):
            return self.setNoMap()

        mx, my = self.locator.getMapBounds(lab)
        self.widget.resize(mx, my)

        for host, (x, y) in self.locator.getMap(lab):
            labelText = host.split('.')[0]

            tooltip = None
            if myHost and host == myHost:
                labelText += '\n<span color="red">You Are Here</span>'
            elif self._shouldHighlightCascader(host, cascaderHosts, subjects):
                cascader = self.cascaders.findCascader(host=host)
                username, (host, subjects) = cascader
                labelText += ('\n<span color="blue" underline="single">'
                              'Cascader</span>')
                tooltip = str(subjects)
            elif host in helpedHosts:
                labelText += ('\n<span color="purple">'
                              'User you are helping</span>')

            y = my - y

            eb = gtk.EventBox()
            label = gtk.Label()
            label.set_markup(labelText)
            eb.add(label)

            if tooltip is not None:
                tooltips = gtk.Tooltips()
                tooltips.set_tip(label, tooltip)

            if onClick is not None:
                eb.connect('button-press-event', onClick, host)

            eb.show_all()
            self.widget.attach(eb, x, x+1, y, y+1)
