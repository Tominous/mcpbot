import logging

from utils.restricted import restricted
from IRCBotBase import IRCBotBase


class TestBot(IRCBotBase):
    def __init__(self, nick='DevBot'):
        IRCBotBase.__init__(self, nick)
        self.logger.setLevel(logging.DEBUG)
        self.whitelist['ProfMobius'] = 5

    def onIRC_Default(self, cmd, prefix, args):
        self.logger.debug('? IRC_%s %s %s', cmd, prefix, str(args))

    def onDefault(self, ev):
        self.logger.debug('? %s_%s %s %s %s', ev.type, ev.cmd, ev.sender, ev.target, repr(ev.msg))

    def onCmd(self, ev):
        self.logger.info('! [%d] %s S: %s C: %s T: %s M: %s', ev.id, ev.type.ljust(4), ev.sender.ljust(20),
                         ev.cmd.ljust(15), ev.target, ev.msg)

        if ev.cmd == 'listusers':
            for key, user in self.users.items():
                self.logger.info(user.get_string())

        if ev.cmd == 'ip':
            nick = ev.msg.split()[0].strip()
            ip = self.getIP(nick)
            self.say(ev.sender, 'User %s, %s' % (nick, ip))

        if ev.cmd == 'dcc':
            self.dcc.dcc(ev.sender)

        if ev.cmd == 'say':
            self.irc.privmsg(ev.msg.split()[0], ' '.join(ev.msg.split()[1:]))

        if ev.cmd == 'notice':
            self.irc.notice(ev.msg.split()[0], ' '.join(ev.msg.split()[1:]))

        if ev.cmd == 'action':
            self.ctcp.action(ev.msg.split()[0], ' '.join(ev.msg.split()[1:]))

        if ev.cmd == 'colors':
            out_msg = ''
            for i in range(16):
                out_msg += '$C%dAAA ' % i
            self.irc.privmsg(ev.msg.split()[0], out_msg)

        if ev.cmd == 'flood':
            self.cmdFlood(ev.sender, ev.chan, ev.msg)

        if ev.cmd == 'exec':
            self.cmdExec(ev.sender, ev.chan, ev.msg)

        if ev.cmd == 'addwhite':
            self.cmdAddWhite(ev.sender, ev.chan, ev.msg)

        if ev.cmd == 'rmwhite':
            self.cmdRemoveWhite(ev.sender, ev.chan, ev.msg)

    def onDCCMsg(self, ev):
        self.dcc.say(ev.sender, ev.msg)

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

    @restricted()
    def cmdExec(self, sender, channel, cmd):
        try:
            self.logger.info(cmd)
            exec cmd in self.globaldic, self.localdic
        except Exception as exc:
            self.logger.exception('ERROR in exec')
            self.say(sender, 'ERROR : %s' % exc)


if __name__ == '__main__':
    bot = TestBot('PMDevBot')
    bot.connect('irc.esper.net')
    bot.irc.join('#test')
    bot.start()
