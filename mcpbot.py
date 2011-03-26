import sqlite3
from irc_lib.IRCBotBase import IRCBotBase

class MCPBot(IRCBotBase):
    
    whitelist = Set(['ProfMobius'])
    
    def __init__(self, nick='DevBot'):
        IRCBotBase.__init__(self, nick)
        
    def onDefault(self, ev):
        pass

    def onCmd(self, ev):
        pass
        
if __name__ == "__main__":
    bot = TestBot('PMDevBot')
    bot.connect('irc.esper.net')
    bot.irc.join('#test')
    bot.startLogging()
    bot.loadWhitelist()
    bot.start()    
