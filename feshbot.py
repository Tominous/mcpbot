import sys
import logging

from irc_lib.ircbot import IRCBotBase
from db_sqlite import DBHandler
from mcpbotcmds import MCPBotCmds


class MCPBot(IRCBotBase):
    def __init__(self, nick='DevBot', char='!', db_name='database.sqlite'):
        IRCBotBase.__init__(self, nick, char, log_level=logging.DEBUG)
        self.debug = True
        self.dbh = DBHandler(db_name)
        self.whitelist['Fesh0r'] = 5

    def onIRC_default(self, cmd, prefix, args):
        self.logger.debug('? IRC_%s %s %s', cmd, prefix, str(args))

    def on_default(self, evt):
        self.logger.debug('? %s_%s %s %s %s', evt.type, evt.cmd, evt.sender, evt.target, repr(evt.msg))

    def on_cmd(self, evt):
        self.logger.info('! [%d] %s S: %s C: %s T: %s M: %s', evt.id, evt.type.ljust(4), evt.sender.ljust(20),
                         evt.cmd.ljust(15), evt.target, evt.msg)
        MCPBotCmds(self, evt, self.dbh).process_cmd()


def main(password):
    bot = MCPBot('FeshBot', '^')
    bot.connect('irc.esper.net')
    bot.nickserv.identify(password)
    bot.irc.join('#test')
    bot.load_whitelist()
    bot.start()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'No password given. Try python feshbot.py <password>.'
        sys.exit(0)
    main(sys.argv[1])
