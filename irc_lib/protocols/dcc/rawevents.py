from irc_lib.protocols.event import Event


class DCCRawEvents(object):
    def onRawDCCMsg(self, ev):
        if not ev.msg:
            return
        self.eventlog(ev)

        if ev.msg != ev.msg.strip():
            self.log('*** DCC.onRawDCCMsg: stripped: %s' % repr(ev.msg))
            ev.msg = ev.msg.strip()
        if len(ev.msg) > 1:
            if ev.msg[0] == self.bot.controlchar:
                ev.msg = ev.msg[1:]
            if len(ev.msg.split()) < 2:
                outmsg = ' '
            else:
                outmsg = ' '.join(ev.msg.split()[1:])
            outev = Event(ev.sender, ev.msg.split()[0], self.cnick, outmsg, 'CMD')
            self.bot.commandq.put(outev)

    def onDCC_CHAT(self, ev):
        nick = ev.sender
        args = ev.msg.split()
        if len(args) != 3:
            self.log('*** DCC.onDCC_CHAT: INVALID: %s %s %s' % (ev.sender, ev.target, repr(ev.msg)))
            return
        dccprot = args[0]
        dccip = self.conv_ip_long_std(args[1])
        dccport = int(args[2])

        self.log("onDCC_CHAT: %s %s | IP:%s Port:%s" % (ev.sender, repr(ev.msg), dccip, dccport))

#

    def onDCC_Default(self, ev):
        self.log('RAW DCC EVENT: %s %s %s %s' % (ev.sender, ev.target, ev.cmd, repr(ev.msg)))
