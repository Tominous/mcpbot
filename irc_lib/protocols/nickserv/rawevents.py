from utils.irc_name import get_nick

class NickServRawEvents(object):

    def onRawNickServSTATUS(self, nseevent, content):
        snick  = content.split()[0]
        status = content.split()[1]

        self.locks['NSStatus'].acquire()        
        if not snick in self.bot.irc_status['Users']:
            self.bot.irc_status['Users'][snick] = {}
        self.bot.irc_status['Users'][snick]['Registered'] = int(status)
        self.bot.irc_status['Users'][snick]['Host'] = -1
        self.bot.irc_status['Users'][snick]['IP']   = -1
        self.locks['NSStatus'].notifyAll()
        self.locks['NSStatus'].release()

            
    def onRawNickServDefault(self, nseevent, content):
        pass
    
