import thread
class IRCBotAdvMtd(object):

    def getIP(self, nick):
        if not nick in self.irc_status['Users']: return -2
        
        self.irc.whois(nick)
        self.locks['WhoIs'].acquire()
        
        while self.irc_status['Users'][nick]['IP'] < 0:
            self.locks['WhoIs'].wait()
        
        self.locks['WhoIs'].release()
        return self.irc_status['Users'][nick]['IP']

    def getStatus(self, nick):
        if not nick in self.irc_status['Users']: return -2
        
        self.nickserv.status(nick)
        self.locks['NSStatus'].acquire()
                
        while self.irc_status['Users'][nick]['Registered'] < 0:
            self.locks['NSStatus'].wait()
        
        self.locks['NSStatus'].release()        
        return self.irc_status['Users'][nick]['Registered']

    def say(self, nick, msg):
        if nick in self.dcc.sockets and self.dcc.sockets[nick]:
            self.dcc.say(nick, msg)
        else:
            self.irc.notice(nick, msg)            

    def raise_onCmd(self, sender, cmd, arguments):
        if hasattr(self, 'onCmd'):
            thread.start_new_thread(getattr(self, 'onCmd'),(sender, cmd, arguments))
        else:
            thread.start_new_thread(getattr(self, 'onDefault'),(sender, cmd, arguments))
                        
