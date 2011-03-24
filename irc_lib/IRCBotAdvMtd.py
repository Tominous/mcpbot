import thread
from protocols.user import User
class IRCBotAdvMtd(object):

    def getIP(self, nick):
        if not nick in self.users: self.users[nick] = User(nick)
        
        self.irc.whois(nick)
        self.locks['WhoIs'].acquire()
        
        while self.users[nick].ip < 0:
            self.locks['WhoIs'].wait()
        
        self.locks['WhoIs'].release()
        return self.users[nick].ip

    def getStatus(self, nick):
        if not nick in self.users: self.users[nick] = User(nick)
        
        self.nickserv.status(nick)
        self.locks['NSStatus'].acquire()
                
        while self.users[nick].status < 0:
            self.locks['NSStatus'].wait()
        
        self.locks['NSStatus'].release()        
        return self.users[nick].status

    def say(self, nick, msg):
        #if not nick in self.users: return
        if nick in self.dcc.sockets and self.dcc.sockets[nick]:     #May have to come back here at some point if the users start holding their own socket
            self.dcc.say(nick, msg)
        else:
            self.irc.notice(nick, msg)            

    def raise_onCmd(self, ev):
        if hasattr(self, 'onCmd'):
            self.threadpool.add_task(getattr(self, 'onCmd'),ev)
        else:
            self.threadpool.add_task(getattr(self, 'onDefault'),ev)
                   
