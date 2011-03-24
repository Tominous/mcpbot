from utils.irc_name import get_nick, get_ip
from protocols.event import Event
from protocols.user import User

class IRCRawEvents(object):
    
    def onRawPING(self, msg):
        self.pong(msg[1])
    
    def onRawNOTICE(self, ev):
        if ev.target == 'AUTH':
            self.bot.irc_status['Server'] = ev.sender
            return

        self.onRawPRIVMSG(ev)

    def onRawPRIVMSG(self, ev):
        
        outcmd = None
        
        if ev.ischan and ev.msg[0] == self.bot.controlchar:
            outcmd = ev.msg.split()[0][1:]
         
        if ev.target == self.cnick and ev.msg[0] != self.bot.controlchar:
            outcmd = ev.msg.split()[0]
        
        if outcmd:
            if len(ev.msg.split()) < 2 : outmsg = ' '
            else: outmsg = ' '.join(ev.msg.split()[1:])
            evcmd = Event(ev.sender, outcmd, ev.target, outmsg, self.cnick, 'CMD')
            self.bot.raise_onCmd(evcmd)            
            
    def onRawJOIN(self, ev):
        if ev.sender == self.cnick:
            self.bot.irc_status['Channels'].add(ev.chan)
        else:
           self.add_user(ev.sender, ev.chan) 
    
    def onRawPART(self, ev):
        self.rm_user(ev.sender, ev.chan)

    def onRawQUIT(self, ev):
        self.rm_user(ev.sender)

    def onRawRPL_MOTDSTART(self, ev):
        if ev.sender == self.bot.irc_status['Server']:
            self.locks['ServReg'].acquire()            
            self.bot.irc_status['Registered'] = True
            self.locks['ServReg'].notifyAll()
            self.locks['ServReg'].release()
    
    def onRawRPL_NAMREPLY(self, ev):
        weirdsymbol = ev.msg.split()[0]     #Used for channel status, "@" is used for secret channels, "*" for private channels, and "=" for others (public channels).
        channel     = ev.msg.split()[1]
        nicks       = ev.msg.split()[2:]

        for nick in nicks:
            self.add_user(nick, channel)
    
    def onRawRPL_WHOISUSER(self, ev):
        nick = ev.msg.split()[0]
        user = ev.msg.split()[1]
        host = ev.msg.split()[2]
        real = ' '.join(ev.msg.split()[4:])[1:]

        self.locks['WhoIs'].acquire()
        if nick in self.bot.users:
            self.bot.users[nick].host = host
            self.bot.users[nick].ip   = get_ip(host)
        self.locks['WhoIs'].notifyAll()
        self.locks['WhoIs'].release()
    
    def onRawNICK(self, ev):
        if ev.sender == self.cnick:return
        self.bot.users[ev.target] = self.bot.users[ev.sender]
        del self.bot.users[ev.sender]

    def onRawINVITE(self, ev):
        self.join(ev.msg)
    
    def onRawDefault(self, ev):
        pass
