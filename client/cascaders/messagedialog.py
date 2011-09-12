import gtk

class MessageDialog:
    '''
    This dialog window that holds messaging information etc

    When the last tab is closed, this will automatically close
    '''
    def __init__(self):
        self.builder = gtk.Builder()
        self.root = self.builder.add_from_file('gui/messaging.glade')

        self.window = self.builder.get_object('wdMessage')
        self.notebook = self.builder.get_object('notebook')
        self.builder.connect_signals(self)

        #holds the message buffers by helpid
        self.messageBuffers = {}

        self.sendMessage = {}

    def addTab(self, helpid, title):
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

    def onTabCloseClicked(self, sender, widget):
        pagenum = self.notebook.page_num(widget)
        self.notebook.remove_page(pagenum)

        if self.notebook.get_n_pages() == 0:
            self.window.hide_all()
    
    def writeMessage(self, helpid, frm, msg):
        buff = self.messageBuffers[helpid]
        text = '[%s] %s\n' % (frm, msg)
        buff.insert(buff.get_end_iter(), text)

    def onSendClicked(self, widget, textbuff, helpid):
        start, end = textbuff.get_bounds()
        text = textbuff.get_text(start, end)
        self.sendMessage[helpid](text)
        self.writeMessage(helpid, 'ME', text)
        textbuff.set_text('')

    def registerMessageCallback(self, helpid, f):
        self.sendMessage[helpid] = f
