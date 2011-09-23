#!/usr/bin/python -O
import os
from subprocess import Popen, PIPE

import labmap

wd = os.path.dirname(__file__)
with open(os.path.join(wd, 'data', 'hosts')) as f:
    locator = labmap.Locator(f)

    for lab in locator.getLabs():
        for host, location in locator.getMap(lab):

            process = Popen(["ssh", host], stdout=PIPE)
            exit_code = os.waitpid(process.pid, 0)
            output = process.communicate()[0]
            
            if 'Name or service not known' in output:
                print 'Lookup of %s failed' % host
