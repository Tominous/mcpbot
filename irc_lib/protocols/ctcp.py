import time
import logging

from irc_lib.event import Event
from irc_lib.protocol import Protocol
from irc_lib.protocols.dcc import DCCProtocol


CTCP_DELIMITER = '\001'


class CTCPProtocol(Protocol):
    def __init__(self, _nick, _locks, _bot, _parent):
        Protocol.__init__(self, _nick, _locks, _bot, _parent, 'IRCBot.CTCP')
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

        ev = Event(prefix, cmd, target, data, 'CTCP')

        cmd_func = getattr(self, 'onCTCP_%s' % ev.cmd, self.onCTCP_Default)
        cmd_func(ev)

        cmd_func = getattr(self.bot, 'onCTCP_%s' % ev.cmd, getattr(self.bot, 'onCTCP_Default', self.bot.onDefault))
        cmd_func(ev)

    def onCTCP_DCC(self, ev):
        self.dcc.process_msg(ev.senderfull, ev.target, ev.msg)

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
        self.logger.info('RAW CTCP EVENT: %s %s %s %s', ev.sender, ev.target, ev.cmd, repr(ev.msg))

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