from irc_lib.utils.irc_name import get_nick
import socket
import time,os
from irc_lib.protocols.event import Event
from irc_lib.protocols.user import User

class DCCRawEvents(object):

    def onRawDCCMsg(self, ev):
        if not ev.msg: return
        if self.bot.log:
            self.bot.loggingq.put(ev)

        ev.msg = ev.msg.strip()
        if len(ev.msg) > 1:
            if ev.msg[0] == self.bot.controlchar: ev.msg = ev.msg[1:]
            if len(ev.msg.split()) < 2: outmsg = ' '
            else: outmsg = ' '.join(ev.msg.split()[1:])
            outev = Event(ev.sender, ev.msg.split()[0], self.cnick, outmsg, self.cnick, 'CMD')

            self.bot.commandq.put(outev)

    def onRawDCCCHAT(self, sender, dcccmd, dccarg, dccip, dccport):
        nick    = get_nick(sender)
        dccip   = self.conv_ip_long_std(int(dccip))
        #dccip   = '192.168.178.40'
        dccport = int(dccport)

        try:
            self.sockets[nick] = socket.socket()
            self.sockets[nick].connect((dccip, dccport))
            self.sockets[nick].setblocking(0)
            self.buffers[nick] = ''
        except KeyError, msg:
            print '[DCCRawEvents.onRawDCCChat] Nick not found in socket table : %s'%nick


        #print '%s %s | IP:%s Port:%s'%(dcccmd, dccarg, dccip, dccport)


    def onRawDCCDefault(self, sender, dcccmd, dccarg, dccip, dccport):
        print 'RAW EVENT'
