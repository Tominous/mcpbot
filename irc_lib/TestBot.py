import time
import cmd as cprompt
from utils.irc_name import get_nick

from IRCBotBase import IRCBotBase

class TestBot(IRCBotBase, cprompt.Cmd):
    
    def __init__(self, nick='DevBot'):
        IRCBotBase.__init__(self, nick)
        cprompt.Cmd.__init__(self)
    
    def onDefault(self, sender, cmd, msg):
        pass

    def onCmd(self, sender, cmd, args):
        print '%s => [%s] [%s]'%(sender,cmd,args)

        if cmd == 'ip':
            nick = args.split()[0]
            ip = self.getIP(nick)
            print nick,ip
            self.say(sender.split('!')[0], 'User %s, %s'%(nick, self.irc_status['Users'][nick]['IP']))

    def onJOIN(self, sender, cmd, msg):
        channel_name = msg[1:]
        if get_nick(sender) == self.cnick:
            self.ctcp.action(channel_name, 'greats everyone.')
        elif channel_name != "#test":
            self.irc.privmsg(channel_name, 'Hello %s!'%get_nick(sender))
    
    def onPRIVMSG(self, sender, cmd, msg):
        print sender, cmd, msg
        channel_name = msg.split()[0]
        msg          = ' '.join(msg.split()[1:])


        if msg.split()[0][1:] == ':status':
            nick = msg.split()[1]
            self.getStatus(nick)
            self.irc.notice(channel_name, 'User %s : %s'%(nick, self.irc_status['Users'][nick]['Registered']))
        
        if msg.split()[0][1:] == ':dcc':
            self.dcc.dcc(get_nick(sender))
        
        if msg.split()[0][1:] == ':dccsay':
            self.dcc.say(get_nick(sender), ' '.join(msg.split()[1:]))
        
        if msg.split()[0][1:] == ':whois':
            self.irc.whois(get_nick(sender))
        
        if msg.split()[0][1:] == ':getnick':
            if len(msg.split()) > 1:
                nick = msg.split()[1]
                if not nick in self.irc_status['Users']:
                    self.irc.notice(channel_name, 'User %s not found.'%(nick))
                else:
                    self.irc.notice(channel_name, 'User %s : %d'%(msg.split()[1],self.getStatus(nick)))
        if msg.split()[0][1:] == ':getuser':
                self.irc.notice(channel_name, 'User %s : %s'%(msg.split()[1],self.irc_status['Users'][msg.split()[1]]))
        elif msg.split()[0][1:] == ':cmd':
            if len(msg.split()) > 2:
                cmd   = msg.split()[1]
                args  = msg.split()[2:]
                    
                if hasattr(self.irc, cmd):
                    getattr(self.irc, cmd)(*tuple(args))
                else:
                    self.irc.notice(channel_name, 'Unknown command.')
            
                
    def onNickServSTATUS(self, nseevent, content):
        print 'RECEIVED AN ANSWER FROM NICKSERV : %s %s'%(nseevent, content)


if __name__ == "__main__":
    bot = TestBot('PMDevBot')
    #bot.start()
    bot.connect('irc.esper.net')
    bot.irc.join('#test')
    bot.nickserv.status('ProfMobius')


    while True: time.sleep(1)
