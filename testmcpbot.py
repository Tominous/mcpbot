import sys
import logging

from irc_lib.ircbot import IRCBotBase
from mcpbotcmds import MCPBotCmds


class MCPBot(IRCBotBase, MCPBotCmds):

    def __init__(self, nick='DevBot', char='!'):
        IRCBotBase.__init__(self, nick, char)
        self.logger.setLevel(logging.DEBUG)
        self.whitelist['ProfMobius'] = 5

    def onIRC_Default(self, cmd, prefix, args):
        self.logger.debug('? IRC_%s %s %s', cmd, prefix, str(args))

    def onDefault(self, ev):
        self.logger.debug('? %s_%s %s %s %s', ev.type, ev.cmd, ev.sender, ev.target, repr(ev.msg))

    def onCmd(self, ev):
        self.logger.info('! [%d] %s S: %s C: %s T: %s M: %s', ev.id, ev.type.ljust(4), ev.sender.ljust(20),
                         ev.cmd.ljust(15), ev.target, ev.msg)
        cmd = ev.cmd.lower()
        cmd_func = getattr(self, 'cmd_%s' % cmd, self.cmdDefault)
        cmd_func(ev.sender, ev.chan, ev.cmd, ev.msg)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'No password given. Try python mcpbot.py <password>.'
        sys.exit(0)

    bot = MCPBot('MCPBot_NG', '$')
    bot.connect('irc.esper.net')
    bot.nickserv.identify(sys.argv[1])
    bot.irc.join('#test')
    bot.loadWhitelist()

    bot.start()
