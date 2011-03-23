from utils.irc_name import get_nick, get_ip

class IRCRawEvents(object):
    
    def onRawPING(self, msg):
        self.pong(msg[1])
    
    def onRawNOTICE(self, sender, cmd, msg):
        if msg.split()[0] == 'AUTH':
            self.bot.irc_status['Server'] = sender
            return

        target = msg.split()[0]
        body   = ' '.join(msg.split()[1:])[1:]
        if target[0] in ['#','&'] and body[0] == self.bot.controlchar:
            self.bot.raise_onCmd(sender.strip(), body.split()[0][1:].strip(), ' '.join(body.split()[1:]).strip())
            return
        
        if target == self.cnick and body[0] != self.bot.controlchar:
            self.bot.raise_onCmd(sender.strip(), body.split()[0].strip(), ' '.join(body.split()[1:]).strip())
            return

    def onRawPRIVMSG(self, sender, cmd, msg):
        target = msg.split()[0]
        body   = ' '.join(msg.split()[1:])[1:]
        if target[0] in ['#','&'] and body[0] == self.bot.controlchar:
            self.bot.raise_onCmd(sender.strip(), body.split()[0][1:].strip(), ' '.join(body.split()[1:]).strip())
            return
        
        if target == self.cnick and body[0] != self.bot.controlchar:
            self.bot.raise_onCmd(sender.strip(), body.split()[0].strip(), ' '.join(body.split()[1:]).strip())
            return
            
    def onRawJOIN(self, sender, cmd, msg):
        channel = msg[1:]
        if get_nick(sender) == self.cnick:
            self.bot.irc_status['Channels'].add(channel)
        else:
           self.add_user(get_nick(sender), channel) 
    
    def onRawPART(self, sender, cmd, msg):
        channel = msg.split()[0]
        self.rm_user(get_nick(sender), channel)

    def onRawQUIT(self, sender, cmd, msg):
        self.rm_user(get_nick(sender))
    
    def onRawRPL_MOTDSTART(self, sender, cmd, msg):
        if sender == self.bot.irc_status['Server']:
            self.locks['ServReg'].acquire()            
            self.bot.irc_status['Registered'] = True
            self.locks['ServReg'].notifyAll()
            self.locks['ServReg'].release()
    
    def onRawRPL_NAMREPLY(self, sender, cmd, msg):
        channel = msg.split()[2]
        nicks   = msg.split()[3:]
        nicks[0]= nicks[0][1:]
        for nick in nicks:
            self.add_user(nick, channel)
            #self.whois(nick)                #Automatic whois ?
    
    def onRawRPL_WHOISUSER(self, send, cmd, msg):
        nick = msg.split()[1]
        real = msg.split()[2]
        host = msg.split()[3]

        self.locks['WhoIs'].acquire()
        if nick in self.bot.irc_status['Users']:
            self.bot.irc_status['Users'][nick]['Host'] = host
            self.bot.irc_status['Users'][nick]['IP']   = get_ip(host)
        self.locks['WhoIs'].notifyAll()
        self.locks['WhoIs'].release()
    
    def onRawNICK(self, sender, cmd, msg):
        last_nick = get_nick(sender)
        new_nick  = msg[1:]

        if last_nick == self.cnick:return
        self.bot.irc_status['Users'][new_nick] = self.bot.irc_status['Users'][last_nick]
        del self.bot.irc_status['Users'][last_nick]
    
    def onRawINVITE(self, sender, cmd, msg):
        chan = msg.split()[1][1:]
        self.join(chan)
    
    def onRawDefault(self, sender, cmd, msg):
        pass
