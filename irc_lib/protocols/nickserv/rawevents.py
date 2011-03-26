from irc_lib.utils.irc_name import get_nick
from irc_lib.protocols.user import User

class NickServRawEvents(object):

    def onRawNickServSTATUS(self, ev):
        snick  = ev.msg.split()[0]
        status = ev.msg.split()[1]

        self.locks['NSStatus'].acquire()        
        if not snick in self.bot.users: self.bot.users[nick] = User(nick)
        self.bot.users[snick].status = int(status)
        self.locks['NSStatus'].notifyAll()
        self.locks['NSStatus'].release()

            
    def onRawNickServDefault(self, ev):
        pass
    
