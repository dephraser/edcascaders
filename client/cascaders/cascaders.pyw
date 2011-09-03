import logging

import wx

from mainframe import CascadersFrame

class CascadersApp(wx.App):
    def OnInit(self):
        CascadersFrame().Show()
        return True

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    CascadersApp().MainLoop()
