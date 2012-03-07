import time


class CTCPRawEvents(object):
    def onCTCP_DCC(self, ev):
        self.dcc.process_msg(ev)

    def onCTCP_VERSION(self, ev):
        self.ctcp_notice(ev.sender, 'VERSION', 'PMIrcLib:0.1:Python')

    def onCTCP_USERINFO(self, ev):
        self.ctcp_notice(ev.sender, 'USERINFO', 'I am a bot.')

    def onCTCP_CLIENTINFO(self, ev):
        self.ctcp_notice(ev.sender, 'CLIENTINFO', 'PING VERSION TIME USERINFO CLIENTINFO')

    def onCTCP_PING(self, ev):
        self.ctcp_notice(ev.sender, 'PING', ev.msg)

    def onCTCP_TIME(self, ev):
        self.ctcp_notice(ev.sender, 'TIME', time.ctime())

    def onCTCP_ACTION(self, ev):
        pass

    def onCTCP_Default(self, ev):
        self.log("RAW CTCP EVENT: %s %s %s '%s'" % (ev.sender, ev.target, ev.cmd, ev.msg))
