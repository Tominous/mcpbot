import time
from constants import CTCP_DELIMITER


class CTCPCommands(object):
    def ctcp_privmsg(self, target, tag, data=None):
        if data:
            msg = tag + ' ' + data
        else:
            msg = tag
        msg = CTCP_DELIMITER + msg + CTCP_DELIMITER
        self.bot.irc.privmsg(target, msg, color=False)

    def ctcp_notice(self, target, tag, data=None):
        if data:
            msg = tag + ' ' + data
        else:
            msg = tag
        msg = CTCP_DELIMITER + msg + CTCP_DELIMITER
        self.bot.irc.notice(target, msg, color=False)

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
