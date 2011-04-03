from sets               import Set
from irc_lib.IRCBotBase import IRCBotBase
from mcpbotcmds         import MCPBotCmds
import pickle
import sys

class MCPBot(IRCBotBase, MCPBotCmds):
    
    def __init__(self, nick='DevBot', char='!'):
        IRCBotBase.__init__(self, nick, char)
        self.whitelist['ProfMobius'] = 5
        
    def onDefault(self, ev):
        pass
        #self.printq.put('%s S: %s C: %s T: %s M: %s'%(ev.type.ljust(5), ev.sender.ljust(25), ev.cmd.ljust(15), ev.target, ev.msg))        

    def onCmd(self, ev):
        self.printq.put('> [%.2f][%d] %s S: %s C: %s T: %s M: %s'%(ev.stamp, ev.id, ev.type.ljust(5), ev.sender.ljust(25), ev.cmd.ljust(15), ev.target, ev.msg))        
        cmd = ev.cmd.lower()
        try:
            getattr(self, 'cmd_%s'%cmd )(ev.sender, ev.chan, ev.cmd, ev.msg)
        except AttributeError:
            getattr(self, 'cmdDefault')(ev.sender, ev.chan, ev.cmd, ev.msg)
        
if __name__ == "__main__":
    if len(sys.argv) < 2 :
        print 'No password given. Try python mcpbot.py <password>.'
        sys.exit(0)
    
    bot = MCPBot('MCPBot_NG', '$')
    bot.connect('irc.esper.net')
    bot.nickserv.identify(sys.argv[1])
    bot.irc.join('#test')
    bot.startLogging()
    bot.loadWhitelist()
  
    bot.start()    
