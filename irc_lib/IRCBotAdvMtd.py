import thread
import time
import os
import pickle
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
            self.dcc.say(nick, str(msg))
        else:
            self.irc.notice(nick, str(msg))

    def raise_onCmd(self, ev):
        if self.log:
            self.loggingq.put(ev)
        
        if hasattr(self, 'onCmd'):
            self.threadpool.add_task(getattr(self, 'onCmd'),ev)
        else:
            self.threadpool.add_task(getattr(self, 'onDefault'),ev)
                   
    def addWhitelist(self, nick):
        self.whitelist.add(nick)

    def rmWhitelist(self, nick):
        try:
            self.whitelist.remove(nick)
        except KeyError:
            pass

    def saveWhitelist(self, filename = 'whitelist.pck'):
        ff = open(filename, 'w')
        pickle.dump(self.whitelist, ff)
        ff.close()
        
    def loadWhitelist(self, filename = 'whitelist.pck'):
        ff = open(filename, 'r')
        self.whitelist = pickle.load(ff)
        ff.close()

    def startLogging(self, filename = 'bot.log'):
        if not self.log:
            self.log = open(filename, 'a')
        
    def stopLogging(self):
        if self.log:
            self.log.close()
            self.log = None
