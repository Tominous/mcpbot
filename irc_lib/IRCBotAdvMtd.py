import thread
import time
import os
import pickle
from protocols.user import User


class IRCBotAdvMtd(object):

    def getIP(self, nick):
        if not nick in self.users:
            self.users[nick] = User(nick)

        self.irc.whois(nick)
        self.locks['WhoIs'].acquire()

        while self.users[nick].ip < 0:
            self.locks['WhoIs'].wait()

        self.locks['WhoIs'].release()
        return self.users[nick].ip

    def getStatus(self, nick):
        if not nick in self.users:
            self.users[nick] = User(nick)

        self.nickserv.status(nick)
        self.locks['NSStatus'].acquire()

        while self.users[nick].status < 0:
            self.locks['NSStatus'].wait()

        self.locks['NSStatus'].release()
        return self.users[nick].status

    def say(self, nick, msg):
        if not msg:
            return
        #if not nick in self.users: return
        if nick in self.dcc.sockets and self.dcc.sockets[nick]:     #May have to come back here at some point if the users start holding their own socket
            self.dcc.say(nick, str(msg))
        elif nick[0] in ['#', '&']:
            self.irc.privmsg(nick, msg)
        else:
            self.irc.notice(nick, msg)

    def addWhitelist(self, nick, level=4):
        self.whitelist[nick] = level

    def rmWhitelist(self, nick):
        del self.whitelist[nick]

    def saveWhitelist(self, filename = 'whitelist.pck'):
        ff = open(filename, 'w')
        pickle.dump(self.whitelist, ff)
        ff.close()

    def loadWhitelist(self, filename = 'whitelist.pck'):
        try:
            ff = open(filename, 'r')
            self.whitelist = pickle.load(ff)
            ff.close()
        except:
            pass

    def startLogging(self, filename = 'bot.log'):
        if not self.log:
            self.log = open(filename, 'a')

    def stopLogging(self):
        if self.log:
            self.log.close()
            self.log = None

