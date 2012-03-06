import time
from constants import CTCP_DELIMITER


class CTCPCommands(object):
    def rawcmd(self, target, cmd):
        self.out_msg.put(':%s PRIVMSG %s :%s%s\%s' % (self.cnick, target, CTCP_DELIMITER, cmd, CTCP_DELIMITER))

    def rawnotice(self, target, cmd):
        self.out_msg.put(':%s NOTICE %s :%s%s%s' % (self.cnick, target, CTCP_DELIMITER, cmd, CTCP_DELIMITER))

    def time(self, target):
        self.rawcmd(target, 'TIME')

    def action(self, channel, text):
        self.rawcmd(channel, 'ACTION %s' % text)

    def finger(self, target):
        self.rawcmd(target, 'FINGER')

    def version(self, target):
        self.rawcmd(target, 'VERSION')

    def source(self, target):
        self.rawcmd(target, 'SOURCE')

    def userinfo(self, target):
        self.rawcmd(target, 'USERINFO')

    def clientinfo(self, target):
        self.rawcmd(target, 'CLIENTINFO')

    def errmsg(self):
        pass

    def ping(self, target):
        self.rawcmd(target, 'CLIENTINFO %s' % time.time())
