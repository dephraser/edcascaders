import os
from logging import debug

import gtk


class MessageDialog:
    '''
    This dialog window that holds messaging information etc

    When the last tab is closed, this will automatically close
    '''
    def __init__(self):
        self.builder = gtk.Builder()

        dr = os.path.dirname(__file__)
        self.builder.add_from_file(os.path.join(dr, 'gui', 'messaging.glade'))

        self.window = self.builder.get_object('wdMessage')
        self.notebook = self.builder.get_object('notebook')
        self.builder.connect_signals(self)

        #holds the message buffers by helpid
        self.messageBuffers = {}

        self.sendMessage = {}

    def addTab(self, helpid, title):
        '''
        Adds a tab with a close button
        '''
        #hbox will be used to store a label and button, as notebook tab title
        hbox = gtk.HBox(False, 0)
        label = gtk.Label(title)
        hbox.pack_start(label)

        closeImage = gtk.image_new_from_stock(gtk.STOCK_CLOSE,
                                              gtk.ICON_SIZE_MENU)
        
        #close button
        btn = gtk.Button()
        btn.set_relief(gtk.RELIEF_NONE)
        btn.set_focus_on_click(False)
        btn.add(closeImage)
        hbox.pack_start(btn, False, False)
        
        #this reduces the size of the button
        style = gtk.RcStyle()
        style.xthickness = 0
        style.ythickness = 0
        btn.modify_style(style)

        hbox.show_all()

        #this is a bit nasty, but it ensures we aren't reusing an object
        b = gtk.Builder()
        b.add_from_file('gui/messaging.glade')
        widget = b.get_object('frMessageFrame')
        self.messageBuffers[helpid] = b.get_object('tbMessages')
        widget.unparent()
        widget.show_all()
        
        self.notebook.insert_page(widget, hbox)
        
        textbuff = b.get_object('tbCurrentInput')
        send = b.get_object('btSend')
        send.connect('clicked', self.onSendClicked, textbuff, helpid)

        btn.connect('clicked', self.onTabCloseClicked, widget)

        i = b.get_object('txCurrentInput')
        i.connect('key-press-event', self.onKeyPress, textbuff, helpid)

    def onKeyPress(self, window, event, textbuff, helpid):
        ''' Remap enter to send, shift+enter to new line '''
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Return":
            #use shift for a new line, so if shift pressed ignore
            if event.state & gtk.gdk.SHIFT_MASK:
                return
            self.onSendClicked(None, textbuff, helpid)
            return True

        
    def onTabCloseClicked(self, sender, widget):
        ''' 
        Function hides window when last dialog is closed as there is nothing
        else to display
        '''
        pagenum = self.notebook.page_num(widget)
        self.notebook.remove_page(pagenum)

        if self.notebook.get_n_pages() == 0:
            self.window.hide_all()
    
    def onSendClicked(self, widget, textbuff, helpid):
        start, end = textbuff.get_bounds()
        text = textbuff.get_text(start, end)
        self.sendMessage[helpid](text)
        self.writeMessage(helpid, 'ME', text)
        textbuff.set_text('')

    def writeMessage(self, helpid, frm, msg):
        '''
        Writes a message to the correct message box 
        '''
        buff = self.messageBuffers[helpid]
        text = '[%s] %s\n' % (frm, msg)
        buff.insert(buff.get_end_iter(), text)

    def registerMessageCallback(self, helpid, f):
        '''
        Registers a callback that is called when the user enters text
        to send to the server
        '''
        self.sendMessage[helpid] = f
