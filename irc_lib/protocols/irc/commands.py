import constants as cst

class IRCCommands(object):
    
    def rawcmd(self, cmd):
        self.out_msg.put(':%s %s\r\n'%(self.cnick, cmd))    

    def password(self, password='thisisapassword'):
        self.rawcmd('PASS %s'%password)
        
    def nick(self, nick=None):
        if not nick: nick = self.cnick
        self.rawcmd('NICK %s'%nick)
        
    def user(self, user=None, host=None, server=None, real=None):
        if not user or not host or not server or not real:
            user = self.cnick
            host = self.cnick
            server = self.cnick
            real   = ':%s'%self.cnick.upper()
        self.rawcmd('USER %s %s %s %s'%(user,host,server,real))

    def pong(self, timestamp):
        self.rawcmd('PONG %s'%timestamp)

    def join(self, chan, key=''):
        if self.bot.irc_status['Registered']:
            self.rawcmd('JOIN %s %s'%(chan,key))
        else:
            self.pending_actions.put((self.rawcmd, ('JOIN %s %s'%(chan,key),), "self.irc_status['Registered']"))

    def privmsg(self, target, msg):
        self.rawcmd('PRIVMSG %s :%s'%(target, msg))

    def notice(self, target, msg):
        self.rawcmd('NOTICE %s :%s'%(target, msg))

    def names(self, channels=''):
        self.rawcmd('NAMES %s'%(channels))

    def kick(self, chan, nick, comment=''):
        self.rawcmd('KICK %s %s %s'%(chan, nick, comment))
