'''
This is a bit messy, but this is a set of utility functions
'''
import gtk 

from logging import error

def errorDialog(msg):
        error(msg)
        md = gtk.MessageDialog(None, 
                               gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, 
                               gtk.BUTTONS_CLOSE, msg)
        md.run()
        md.destroy()

def getComboBoxText(cb):
    model = cb.get_model()
    itr = cb.get_active_iter()
    return model.get_value(itr, 0)

def initTreeView(tv):
    column = gtk.TreeViewColumn()
    cell = gtk.CellRendererText()
    column.pack_start(cell)
    column.add_attribute(cell,'text',0)
    tv.append_column(column)
