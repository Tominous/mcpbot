import sys
import time
from irc_lib.IRCBotBase import IRCBotBase
from mcpbotcmds import MCPBotCmds


class MCPBot(IRCBotBase, MCPBotCmds):
    def __init__(self, nick='DevBot', char='!'):
        IRCBotBase.__init__(self, nick, char)
        self.whitelist['Fesh0r'] = 5
        self.rawmsg = True

    def onIRC_Default(self, command, prefix, args):
        self.log("IRC_%s %s %s" % (command, prefix, str(args)))

    def onDefault(self, ev):
        self.log("%s_%s %s %s '%s'" % (ev.type, ev.cmd, ev.sender, ev.target, ev.msg))

    def onCmd(self, ev):
        self.log('> [%.2f][%d] %s S: %s C: %s T: %s M: %s' % (ev.stamp, ev.id, ev.type.ljust(5), ev.sender.ljust(25), ev.cmd.ljust(15), ev.target, ev.msg))
        cmd = ev.cmd.lower()
        try:
            getattr(self, 'cmd_%s' % cmd)(ev.sender, ev.chan, ev.cmd, ev.msg)
        except AttributeError:
            getattr(self, 'cmdDefault')(ev.sender, ev.chan, ev.cmd, ev.msg)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print 'No password given. Try python feshbot.py <password>.'
        sys.exit(0)

    bot = MCPBot('FeshBot', '^')
    bot.connect('irc.esper.net')
    bot.nickserv.identify(sys.argv[1])
    bot.log('plz wait')
    time.sleep(5)
    bot.log('joining channels')
    bot.irc.join('#test')
    bot.loadWhitelist()
    bot.start()
