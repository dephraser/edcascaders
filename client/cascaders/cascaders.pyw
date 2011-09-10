'''
Startup file, responsible for setting up the application and starting the gui
'''

import logging

import gtk

from mainframe import CascadersFrame

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    win = CascadersFrame()
    gtk.main()
