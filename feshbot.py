import sys
import logging

from irc_lib.ircbot import IRCBotBase
from dbhandler import DBHandler
from mcpbotcmds import MCPBotCmds


class MCPBot(IRCBotBase):
    def __init__(self, nick='DevBot', char='!', db_name='database.sqlite'):
        IRCBotBase.__init__(self, nick, char, _log_level=logging.DEBUG)
        self.db = DBHandler(db_name)
        self.whitelist['Fesh0r'] = 5

    def onIRC_Default(self, cmd, prefix, args):
        self.logger.debug('? IRC_%s %s %s', cmd, prefix, str(args))

    def onDefault(self, ev):
        self.logger.debug('? %s_%s %s %s %s', ev.type, ev.cmd, ev.sender, ev.target, repr(ev.msg))

    def onCmd(self, ev):
        self.logger.info('! [%d] %s S: %s C: %s T: %s M: %s', ev.id, ev.type.ljust(4), ev.sender.ljust(20),
                         ev.cmd.ljust(15), ev.target, ev.msg)
        MCPBotCmds(self, ev).process_cmd()


def main(password):
    bot = MCPBot('FeshBot', '^')
    bot.connect('irc.esper.net')
    bot.nickserv.identify(password)
    bot.irc.join('#test')
    bot.loadWhitelist()
    bot.start()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'No password given. Try python feshbot.py <password>.'
        sys.exit(0)
    main(sys.argv[1])
