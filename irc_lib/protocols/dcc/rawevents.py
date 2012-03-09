from irc_lib.protocols.event import Event


class DCCRawEvents(object):
    def onRawDCCMsg(self, ev):
        if ev.msg != ev.msg.strip():
            self.logger.warn('*** DCC.onRawDCCMsg: stripped: %s', repr(ev.msg))
            ev.msg = ev.msg.strip()

        if not ev.msg:
            return

        if ev.msg[0] == self.bot.controlchar:
            ev.msg = ev.msg[1:]
        if len(ev.msg.split()) < 2:
            outmsg = ' '
        else:
            outmsg = ' '.join(ev.msg.split()[1:])
        outev = Event(ev.sender, ev.msg.split()[0], self.cnick, outmsg, 'CMD')
        self.bot.commandq.put(outev)

#

    def onDCC_Default(self, ev):
        self.logger.info('RAW DCC EVENT: %s %s %s %s', ev.sender, ev.target, ev.cmd, repr(ev.msg))
