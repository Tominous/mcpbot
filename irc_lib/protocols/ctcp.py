import time

from irc_lib.event import Event
from irc_lib.protocol import Protocol
from irc_lib.protocols.dcc import DCCProtocol


CTCP_DELIMITER = '\001'


class CTCPProtocol(Protocol):
    def __init__(self, nick, locks, bot, parent):
        Protocol.__init__(self, nick, locks, bot, parent, 'IRCBot.CTCP')
        self.irc = self.parent
        self.dcc = DCCProtocol(self.cnick, self.locks, self.bot, self)

    def process_msg(self, prefix, target, msg):
        # remove leading/trailing CTCP_DELIMITER
        if msg[-1] == CTCP_DELIMITER:
            msg = msg[1:-1]
        else:
            self.logger.warn('*** CTCP.process_msg: no trailing delim: %s', repr(msg))
            msg = msg[1:]

        if not msg:
            return

        cmd, _, data = msg.partition(' ')

        evt = Event(prefix, cmd, target, data, 'CTCP')

        cmd_func = getattr(self, 'onCTCP_%s' % evt.cmd, self.onCTCP_default)
        cmd_func(evt)

        cmd_func = getattr(self.bot, 'onCTCP_%s' % evt.cmd, getattr(self.bot, 'onCTCP_default', self.bot.on_default))
        cmd_func(evt)

    def onCTCP_DCC(self, evt):
        self.dcc.process_msg(evt.senderfull, evt.target, evt.msg)

    def onCTCP_VERSION(self, evt):
        self.ctcp_notice(evt.sender, 'VERSION', 'PMIrcLib:0.1:Python')

    def onCTCP_USERINFO(self, evt):
        self.ctcp_notice(evt.sender, 'USERINFO', 'I am a bot.')

    def onCTCP_CLIENTINFO(self, evt):
        self.ctcp_notice(evt.sender, 'CLIENTINFO', 'PING VERSION TIME USERINFO CLIENTINFO')

    def onCTCP_PING(self, evt):
        self.ctcp_notice(evt.sender, 'PING', evt.msg)

    def onCTCP_TIME(self, evt):
        self.ctcp_notice(evt.sender, 'TIME', time.ctime())

    def onCTCP_ACTION(self, evt):
        pass

    def onCTCP_default(self, evt):
        self.logger.info('RAW CTCP EVENT: %s %s %s %s', evt.sender, evt.target, evt.cmd, repr(evt.msg))

    def ctcp_privmsg(self, target, tag, data=None):
        if data:
            msg = tag + ' ' + data
        else:
            msg = tag
        msg = CTCP_DELIMITER + msg + CTCP_DELIMITER
        self.irc.privmsg(target, msg, color=False)

    def ctcp_notice(self, target, tag, data=None):
        if data:
            msg = tag + ' ' + data
        else:
            msg = tag
        msg = CTCP_DELIMITER + msg + CTCP_DELIMITER
        self.irc.notice(target, msg, color=False)

    def time(self, target):
        self.ctcp_privmsg(target, 'TIME')

    def action(self, channel, text):
        self.ctcp_privmsg(channel, 'ACTION', text)

    def version(self, target):
        self.ctcp_privmsg(target, 'VERSION')

    def userinfo(self, target):
        self.ctcp_privmsg(target, 'USERINFO')

    def clientinfo(self, target):
        self.ctcp_privmsg(target, 'CLIENTINFO')

    def ping(self, target):
        self.ctcp_privmsg(target, 'PING', time.time())
