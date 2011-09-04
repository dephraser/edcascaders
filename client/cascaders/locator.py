'''
This class is responsbile for providing location information based on hostname
as well as being able to provide map data
'''

import ConfigParser as configparser

class Locator():

    def __init__(self, fileHandle):
        self.hosts = configparser.ConfigParser(allow_no_value=True)
        self.hosts.readfp(fileHandle)

        self.hostsLab = {}
        for lab in self.hosts.sections():
            for hostname, v in self.hosts.items(lab):
                self.hostsLab[hostname] = lab

    def getLabs(self):
        return self.hosts.sections()

    def labFromHostname(self,hostname):
        return self.hostsLab[hostname]

