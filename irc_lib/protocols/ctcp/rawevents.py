from utils.irc_name import get_nick
import time

class CTCPRawEvents(object):

    def onRawCTCPFINGER(self, sender, ctcpcmd, content):
        self.rawnotice(sender, 'FINGER :I am just an innocent bot!')

    def onRawCTCPVERSION(self, sender, ctcpcmd, content):
        self.rawnotice(sender, 'VERSION PMIrcLib:0.1:Python')
        
    def onRawCTCPSOURCE(self, sender, ctcpcmd, content):
        self.rawnotice(sender, 'SOURCE Nowhere:None:None')
        self.rawnotice(sender, 'SOURCE')

    def onRawCTCPUSERINFO(self, sender, ctcpcmd, content):
        self.rawnotice(sender, 'USERINFO :I am a bot.')


    def onRawCTCPPING(self, sender, ctcpcmd, content):
        self.rawnotice(sender, 'PING :%s'%content)

    def onRawCTCPTIME(self, sender, ctcpcmd, content):
        self.rawnotice(sender, 'TIME :%s'%time.ctime())

    def onRawCTCPDefault(self, sender, ctcpcmd, content):
        print 'RAW EVENT'
