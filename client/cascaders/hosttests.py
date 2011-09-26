#!/usr/bin/python -O
import os
from subprocess import Popen, PIPE

import labmap

wd = os.path.dirname(__file__)
with open(os.path.join(wd, 'data', 'hosts')) as f:
    locator = labmap.Locator(f)

    for lab in locator.getLabs():
        for host, location in locator.getMap(lab):

            (c_stdin,c_stdout,c_stderr) = os.popen3('ssh %s' % host,'r')
            out = c_stdout.read()
            err = c_stderr.read()
            c_stdin.close()
            c_stdout.close()
            c_stderr.close()

            if 'Name or service not known' in err:
                print 'Lookup of %s failed' % host
            else:
                print 'Fine for %s' % host
