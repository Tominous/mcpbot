from utils.irc_name import get_nick

class IRCRawEvents(object):
    
    def onRawPING(self, msg):
        self.pong(msg[1])
    
    def onRawNOTICE(self, sender, cmd, msg):
        if msg.split()[0] == 'AUTH':
            self.bot.irc_status['Server'] = sender
            
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
            self.bot.irc_status['Registered'] = True
    
    def onRawRPL_NAMREPLY(self, sender, cmd, msg):
        channel = msg.split()[2]
        nicks   = msg.split()[3:]
        nicks[0]= nicks[0][1:]
        for nick in nicks:
            self.add_user(nick, channel)
    
    def onRawNICK(self, sender, cmd, msg):
        last_nick = get_nick(sender)
        new_nick  = msg[1:]

        if last_nick == self.cnick:return
        self.bot.irc_status['Users'][new_nick] = self.bot.irc_status['Users'][last_nick]
        del self.bot.irc_status['Users'][last_nick]
    
    def onRawDefault(self, sender, cmd, msg):
        pass
