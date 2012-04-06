import logging

from irc_lib.utils.restricted import restricted
from irc_lib.ircbot import IRCBotBase


class TestBot(IRCBotBase):
    def __init__(self, nick='DevBot'):
        IRCBotBase.__init__(self, nick, _log_level=logging.DEBUG)
        self.whitelist['ProfMobius'] = 5

    def onIRC_Default(self, cmd, prefix, args):
        self.logger.debug('? IRC_%s %s %s', cmd, prefix, str(args))

    def onDefault(self, evt):
        self.logger.debug('? %s_%s %s %s %s', evt.type, evt.cmd, evt.sender, evt.target, repr(evt.msg))

    def onCmd(self, evt):
        self.logger.info('! [%d] %s S: %s C: %s T: %s M: %s', evt.id, evt.type.ljust(4), evt.sender.ljust(20),
                         evt.cmd.ljust(15), evt.target, evt.msg)

        if evt.cmd == 'listusers':
            for user in self.users.values():
                self.logger.info(user.get_string())

        if evt.cmd == 'ip':
            nick = evt.msg.split()[0].strip()
            ip = self.getIP(nick)
            self.say(evt.sender, 'User %s, %s' % (nick, ip))

        if evt.cmd == 'dcc':
            self.dcc.dcc(evt.sender)

        if evt.cmd == 'say':
            self.irc.privmsg(evt.msg.split()[0], ' '.join(evt.msg.split()[1:]))

        if evt.cmd == 'notice':
            self.irc.notice(evt.msg.split()[0], ' '.join(evt.msg.split()[1:]))

        if evt.cmd == 'action':
            self.ctcp.action(evt.msg.split()[0], ' '.join(evt.msg.split()[1:]))

        if evt.cmd == 'colors':
            out_msg = ''
            for i in range(16):
                out_msg += '$C%dAAA ' % i
            self.irc.privmsg(evt.msg.split()[0], out_msg)

        if evt.cmd == 'flood':
            self.cmdFlood(evt.sender, evt.chan, evt.msg)

        if evt.cmd == 'addwhite':
            self.cmdAddWhite(evt.sender, evt.chan, evt.msg)

        if evt.cmd == 'rmwhite':
            self.cmdRemoveWhite(evt.sender, evt.chan, evt.msg)

    def onDCCMsg(self, evt):
        self.dcc.say(evt.sender, evt.msg)

    @restricted()
    def cmdAddWhite(self, sender, channel, msg):
        self.addWhitelist(msg)

    @restricted()
    def cmdRemoveWhite(self, sender, channel, msg):
        self.rmWhitelist(msg)

    @restricted()
    def cmdFlood(self, sender, channel, msg):
        number = int(msg.split()[1])
        for i in range(number):
            self.irc.privmsg(msg.split()[0], ':%03d' % i)


def main():
    bot = TestBot('PMDevBot')
    bot.connect('irc.esper.net')
    bot.irc.join('#test')
    bot.start()

if __name__ == '__main__':
    main()
