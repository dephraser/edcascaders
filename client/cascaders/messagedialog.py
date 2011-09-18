import os

import gtk

from labmap import Map

class MessageDialog:
    '''
    This dialog window that holds messaging information etc

    When the last tab is closed, this will automatically hide itself
    '''
    def __init__(self, locator, cascaders):
        self.locator = locator
        self.cascaders = cascaders

        self.closedPages = {}

        self.builder = gtk.Builder()

        dr = os.path.dirname(__file__)
        self.builder.add_from_file(os.path.join(dr, 'gui', 'messaging.glade'))

        self.window = self.builder.get_object('wdMessage')
        self.notebook = self.builder.get_object('notebook')
        self.builder.connect_signals(self)

        #holds the message buffers by helpid
        self.messageBuffers = {}

        self.sendMessage = {}

    def _getTabLabel(self, title, widget, helpid):
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

        btn.connect('clicked', self.onTabCloseClicked, widget, title, helpid)

        hbox.show_all()
        return hbox

    def addTab(self, helpid, title, myHost, cascHost, iAmCascader):
        '''
        Adds a tab with a close button

        helpid - system wide unique help id
        title - the title of the tab
        myHost - this clients hostname
        cascHost - the other clients hostname
        iAmCascader - true if this client is the cascader
        '''

        #this is a bit nasty, but it ensures we aren't reusing an object
        b = gtk.Builder()
        dr = os.path.dirname(__file__)
        b.add_from_file(os.path.join(dr, 'gui', 'messaging.glade'))
        widget = b.get_object('frMessageFrame')
        self.messageBuffers[helpid] = b.get_object('tbMessages')
        widget.reparent(self.window)
        widget.show_all()

        hbox = self._getTabLabel(title, widget, helpid)

        
        self.notebook.insert_page(widget, hbox)
        
        #send button
        textbuff = b.get_object('tbCurrentInput')
        send = b.get_object('btSend')
        send.connect('clicked', self.onSendClicked, textbuff, helpid)


        #if we can display a map, do so. This allows easier meetups
        mapBtn = b.get_object('btMap')
        myLab = self.locator.labFromHostname(myHost) 
        if myLab is None or myLab != self.locator.labFromHostname(cascHost):
            mapBtn.set_sensitive(False)
        else:
            mapBtn.connect('clicked', self.onMapPressed,
                           myHost, cascHost, iAmCascader)

        #remap some key events
        i = b.get_object('txCurrentInput')
        i.connect('key-press-event', self.onKeyPress, textbuff, helpid)

    def onMapPressed(self, widget, myHost, cascHost, iAmCascader):
        dr = os.path.dirname(__file__)
        builder = gtk.Builder()
        builder.add_from_file(os.path.join(dr, 'gui', 'map.glade'))

        window = builder.get_object('wnMap')

        mapwidget = Map(builder.get_object('tbMap'),
                        self.locator,
                        self.cascaders)

        lab = self.locator.labFromHostname(myHost)

        #pick what to highlight
        helpHost = [cascHost] if iAmCascader else None
        cascHost = [cascHost] if not iAmCascader else []

        mapwidget.applyFilter(lab,
                              myHost = myHost,
                              cascaderHosts=cascHost,
                              helpedHosts=helpHost)

        window.show_all()

    def onKeyPress(self, window, event, textbuff, helpid):
        ''' Remap enter to send, shift+enter to new line '''
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Return":
            #use shift for a new line, so if shift pressed ignore
            if event.state & gtk.gdk.SHIFT_MASK:
                return
            self.onSendClicked(None, textbuff, helpid)
            return True

    def onTabCloseClicked(self, sender, widget, title, helpid):
        ''' 
        Function hides window when last dialog is closed as there is nothing
        else to display
        '''
        pagenum = self.notebook.page_num(widget)
        self.closedPages[helpid] = (title, widget)
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
        Writes a message to the correct message box, if the user
        has closed the dialog, then it will be re-shown
        '''
        buff = self.messageBuffers[helpid]
        text = '[%s] %s\n' % (frm, msg)
        buff.insert(buff.get_end_iter(), text)

        if helpid in self.closedPages:
            title, widget = self.closedPages[helpid]
            hbox = self._getTabLabel(title, widget, helpid)
            self.notebook.insert_page(widget, hbox)
            del self.closedPages[helpid]

        if not self.window.flags() & gtk.VISIBLE:
            self.window.show_all()

    def registerMessageCallback(self, helpid, f):
        '''
        Registers a callback that is called when the user enters text
        to send to the server
        '''
        self.sendMessage[helpid] = f
