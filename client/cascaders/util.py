'''
This is a bit messy, but this is a set of utility functions
'''
import time
from logging import error

import gtk 

def errorDialog(msg):
    '''
    Provides an error message, and logging for the given message
    '''
    error(msg)
    md = gtk.MessageDialog(None, 
                           gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
                           gtk.BUTTONS_CLOSE, msg)
    md.run()
    md.destroy()

def getComboBoxText(cb):
    '''
    Returns the selected value in the select box. Return none on nothing
    selected
    '''
    model = cb.get_model()
    itr = cb.get_active_iter()
    return model.get_value(itr, 0) if itr is not None else None

def initTreeView(tv):
    '''
    creates a dialog box as a list view
    '''
    column = gtk.TreeViewColumn()
    cell = gtk.CellRendererText()
    column.pack_start(cell)
    column.add_attribute(cell, 'text', 0)
    tv.append_column(column)
    tv.set_headers_visible(False)

def generateUnqiueId():
    '''
    This should generate a unique id for the user. It doesn't. But it should
    be good enough for now
    '''
    return str(time.time())
