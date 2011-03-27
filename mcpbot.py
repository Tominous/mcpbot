from sets               import Set
from irc_lib.IRCBotBase import IRCBotBase
from mcpbotcmds         import MCPBotCmds

class MCPBot(IRCBotBase, MCPBotCmds):
    
    whitelist = Set(['ProfMobius'])
    
    def __init__(self, nick='DevBot', char='!'):
        IRCBotBase.__init__(self, nick, char)
        
    def onDefault(self, ev):
        self.printq.put('%s S: %s C: %s T: %s M: %s'%(ev.type.ljust(5), ev.sender.ljust(25), ev.cmd.ljust(15), ev.target, ev.msg))        

    def onCmd(self, ev):
        self.printq.put('%s S: %s C: %s T: %s M: %s'%(ev.type.ljust(5), ev.sender.ljust(25), ev.cmd.ljust(15), ev.target, ev.msg))        
        cmd = ev.cmd.lower()
        cmd = cmd[0].upper() + cmd[1:]
        try:
            getattr(self, 'cmd%s'%cmd )(ev.sender, ev.chan, ev.cmd, ev.msg)
        except AttributeError:
            getattr(self, 'cmdDefault')(ev.sender, ev.chan, ev.cmd, ev.msg)
        
if __name__ == "__main__":
    bot = MCPBot('MCPBot_NG', '$')
    bot.connect('irc.esper.net')
    bot.irc.join('#test')
    bot.startLogging()
    bot.loadWhitelist()
    bot.start()    
