'''
Generic wrapper around the functions that the server provides
'''
import rpyc

class RpcClient:
    def __init__(self, host, port, username, computerHostname):
        #does raise exceptions when cannot connect, 
        self.conn = rpyc.connect(host, port)
  
        try:
            self.user = self.conn.root.userJoin(username, computerHostname, lambda: None)
        except ValueError:
            self.conn.close()
            self.conn = None
            raise

    #--------------------------------------------------------------------------
    # simple functions used on startup
    def getCascaderList(self, callback):
        res = rpyc.async(self.user.getCascaderList)()
        res.add_callback(callback)

    def getSubjectList(self, callback):
        res = rpyc.async(self.user.getSubjectList)()
        res.add_callback(callback)

    #--------------------------------------------------------------------------
    # 
    def addSubjects(self, subjects):
        rpyc.async(self.user.addSubjects)(subjects)

