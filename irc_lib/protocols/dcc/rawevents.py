from utils.irc_name import get_nick
import socket

class DCCRawEvents(object):

    def onRawDCCMsg(self, nick, msg):
        pass

    def onRawDCCCHAT(self, sender, dcccmd, dccarg, dccip, dccport):
        nick    = get_nick(sender)
        dccip   = self.conv_ip_long_std(int(dccip))
        #dccip   = '192.168.178.40'
        dccport = int(dccport)
        
        self.sockets[nick] = socket.socket()
        self.sockets[nick].connect((dccip, dccport))
        self.sockets[nick].setblocking(0)
        self.buffers[nick] = ''
        
        #print '%s %s | IP:%s Port:%s'%(dcccmd, dccarg, dccip, dccport)

    def onRawDCCClose(self, sender, dcccmd, dccarg, dccip, dccport):
        nick    = get_nick(sender)
        self.sockets[nick].close()
        del self.sockets[nick]
        del self.buffers[nick]

        print 'Closing connection with %s'%nick

    def onRawDCCDefault(self, sender, dcccmd, dccarg, dccip, dccport):
        print 'RAW EVENT'
