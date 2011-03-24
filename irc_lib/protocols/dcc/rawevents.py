from utils.irc_name import get_nick
import socket
from protocols.event import Event
from protocols.user import User

class DCCRawEvents(object):

    def onRawDCCMsg(self, ev):
        if ev.msg[0] == self.bot.controlchar: ev.msg = ev.msg[1:]
        if len(ev.msg.split()) < 2: outmsg = ' '
        else: outmsg = ' '.join(ev.msg.split()[1:])
        outev = Event(ev.sender, ev.msg.split()[0], self.cnick, outmsg, self.cnick, 'CMD')

        self.bot.raise_onCmd(outev)

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


    def onRawDCCDefault(self, sender, dcccmd, dccarg, dccip, dccport):
        print 'RAW EVENT'
