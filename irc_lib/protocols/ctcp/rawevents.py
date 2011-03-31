from irc_lib.utils.irc_name import get_nick
import time

class CTCPRawEvents(object):

    def onRawCTCPFINGER(self, ev):
        self.rawnotice(ev.sender, 'FINGER :I am just an innocent bot!')

    def onRawCTCPVERSION(self, ev):
        self.rawnotice(ev.sender, 'VERSION PMIrcLib:0.1:Python')
        
    def onRawCTCPSOURCE(self, ev):
        self.rawnotice(ev.sender, 'SOURCE Nowhere:None:None')
        self.rawnotice(ev.sender, 'SOURCE')

    def onRawCTCPUSERINFO(self, ev):
        self.rawnotice(ev.sender, 'USERINFO :I am a bot.')


    def onRawCTCPPING(self, ev):
        #if not ev.msg: return
        self.rawnotice(ev.sender, 'PING %s'%ev.msg)

    def onRawCTCPTIME(self, ev):
        self.rawnotice(ev.sender, 'TIME :%s'%time.ctime())

    def onRawCTCPDefault(self, ev):
        print 'RAW EVENT'
