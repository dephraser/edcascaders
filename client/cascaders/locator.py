from logging import warn

import ConfigParser as configparser
from collections import defaultdict

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

    def getMapBounds(self, lab):
        try: 
            mx = max([x for h, (x,y) in self.getMap(lab)])
            my = max([y for h, (x,y) in self.getMap(lab)])
            return mx, my
        except ValueError:
            warn('No host info for %s: ' % lab)
            return 0,0

