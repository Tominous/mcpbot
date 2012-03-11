from irc_lib.protocols.event import Event


class DCCRawEvents(object):
    def onRawDCCMsg(self, ev):
        if ev.msg != ev.msg.strip():
            self.logger.warn('*** DCC.onRawDCCMsg: stripped: %s', repr(ev.msg))
            ev.msg = ev.msg.strip()

        if not ev.msg:
            return

        self.bot.process_msg(ev.sender, self.cnick, ev.msg)

#

    def onDCC_Default(self, ev):
        self.logger.info('RAW DCC EVENT: %s %s %s %s', ev.sender, ev.target, ev.cmd, repr(ev.msg))
