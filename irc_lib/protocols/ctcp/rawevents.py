import time


class CTCPRawEvents(object):
    def onCTCP_FINGER(self, ev):
        self.rawnotice(ev.sender, 'FINGER :I am just an innocent bot!')

    def onCTCP_VERSION(self, ev):
        self.rawnotice(ev.sender, 'VERSION PMIrcLib:0.1:Python')

    def onCTCP_SOURCE(self, ev):
        self.rawnotice(ev.sender, 'SOURCE Nowhere:None:None')
        self.rawnotice(ev.sender, 'SOURCE')

    def onCTCP_USERINFO(self, ev):
        self.rawnotice(ev.sender, 'USERINFO :I am a bot.')


    def onCTCP_PING(self, ev):
        self.rawnotice(ev.sender, 'PING %s' % ev.msg)

    def onCTCP_TIME(self, ev):
        self.rawnotice(ev.sender, 'TIME :%s' % time.ctime())

    def onCTCP_Default(self, ev):
        self.log('RAW CTCP EVENT: %s %s %s' % (ev.sender, ev.cmd, ev.msg))
