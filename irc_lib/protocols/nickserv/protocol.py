from utils.irc_name import get_nick
from commands  import NickServCommands
from rawevents import NickServRawEvents
from IRCBotError import IRCBotError
import thread
import time

class NickServProtocol(NickServCommands, NickServRawEvents):

    def __init__(self, _nick, _out_msg, _in_msg, _pending_actions, _bot):
        self.cnick           = _nick
        self.out_msg         = _out_msg
        self.in_msg          = _in_msg
        self.pending_actions = _pending_actions
        self.bot             = _bot
        
        thread.start_new_thread(self.treat_msg,  ())

    def treat_msg(self):
        while True:
            msg = self.in_msg.get()
            self.in_msg.task_done()
                
            msg = msg.split()
                    
            cmd      = msg[1]
            destnick = msg[2]
            nseevent = msg[3][1:]
            content  = ' '.join(msg[4:])

            if cmd not in ['PRIVMSG', 'NOTICE']:
                raise IRCBotError('Invalid reply from NickServ : %s'%msg)
                
            if hasattr(self, 'onRawNickServ%s'%nseevent):
                getattr(self, 'onRawNickServ%s'%nseevent)(nseevent, content)
            else:
                getattr(self, 'onRawNickServDefault')(nseevent, content)

            if hasattr(self.bot, 'onNickServ%s'%nseevent):
                getattr(self.bot, 'onNickServ%s'%nseevent)(nseevent, content)
            else:
                getattr(self.bot, 'onDefault')(msg[0], cmd, ' '.join(msg[2:]))

    def getStatus(self, nick):
        if not nick in self.bot.irc_status['Users']: return -2
        
        while self.bot.irc_status['Users'][nick]['Registered'] < 0:
            self.status(nick)
            time.sleep(1)
        
        return self.bot.irc_status['Users'][nick]['Registered']
