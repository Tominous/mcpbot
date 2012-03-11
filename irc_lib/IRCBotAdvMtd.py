import os
import pickle

from irc_lib.protocols.user import User


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

    def rawcmd(self, msg):
        self.out_msg.put(msg)

    def say(self, nick, msg):
        if not msg:
            return
        # May have to come back here at some point if the users start holding their own socket
        if nick in self.dcc.sockets and self.dcc.sockets[nick]:
            self.dcc.say(nick, str(msg))
        elif nick[0] in ['#', '&']:
            self.irc.privmsg(nick, msg)
        else:
            self.irc.notice(nick, msg)

    def addWhitelist(self, nick, level=4):
        self.whitelist[nick] = level

    def rmWhitelist(self, nick):
        del self.whitelist[nick]

    def saveWhitelist(self, filename='whitelist.pck'):
        with open(filename, 'w') as ff:
            pickle.dump(self.whitelist, ff)

    def loadWhitelist(self, filename='whitelist.pck'):
        if os.path.isfile(filename):
            with open(filename, 'r') as ff:
                self.whitelist = pickle.load(ff)

