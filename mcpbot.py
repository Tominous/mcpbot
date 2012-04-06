import sys
import logging

from irc_lib.ircbot import IRCBotBase
from dbhandler import DBHandler
from mcpbotcmds import MCPBotCmds


class MCPBot(IRCBotBase):
    def __init__(self, nick='DevBot', char='!', db_name='database.sqlite'):
        IRCBotBase.__init__(self, nick, char, _log_level=logging.INFO)
        self.db = DBHandler(db_name)
        self.whitelist['ProfMobius'] = 5
        self.whitelist['Searge'] = 5
        self.whitelist['ZeuX'] = 5
        self.whitelist['Ingis'] = 5
        self.whitelist['Fesh0r'] = 5

    def onIRC_Default(self, cmd, prefix, args):
        self.logger.debug('? IRC_%s %s %s', cmd, prefix, str(args))

    def onDefault(self, evt):
        self.logger.debug('? %s_%s %s %s %s', evt.type, evt.cmd, evt.sender, evt.target, repr(evt.msg))

    def onCmd(self, evt):
        self.logger.info('! [%d] %s S: %s C: %s T: %s M: %s', evt.id, evt.type.ljust(4), evt.sender.ljust(20),
                         evt.cmd.ljust(15), evt.target, evt.msg)
        MCPBotCmds(self, evt).process_cmd()


def main(password):
    bot = MCPBot('MCPBot', '!')
    bot.connect('irc.esper.net')
    bot.nickserv.identify(password)
    bot.irc.join('#test')
    bot.loadWhitelist()
    bot.start()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print 'No password given. Try python mcpbot.py <password>.'
        sys.exit(0)
    main(sys.argv[1])
