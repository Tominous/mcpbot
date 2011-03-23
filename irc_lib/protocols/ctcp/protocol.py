from utils.irc_name import get_nick
from commands  import CTCPCommands
from rawevents import CTCPRawEvents
from IRCBotError import IRCBotError
import thread
import time

class CTCPProtocol(CTCPCommands, CTCPRawEvents):

    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick           = _nick
        self.out_msg         = _out_msg
        self.in_msg          = _in_msg
        self.bot             = _bot
        self.locks           = _locks
        
        thread.start_new_thread(self.treat_msg,  ())

    def treat_msg(self):
        while True:
            msg = self.in_msg.get()
            self.in_msg.task_done()

            msg = msg.split()
            
            sender   = get_nick(msg[0])
            cmd      = msg[1]
            destnick = msg[2]
            if len(msg) == 4:
                ctcpcmd  = msg[3][2:-1]             #We skip both the : and \x01
                content  = ''
            else:
                ctcpcmd  = msg[3][2:]             #We skip both the : and \x01
                content  = ' '.join(msg[4:])[:-1] #We remove the tailing \x01

            if cmd not in ['PRIVMSG', 'NOTICE']:
                raise IRCBotError('Invalid command from CTCP : %s'%msg)
                
            if hasattr(self, 'onRawCTCP%s'%ctcpcmd):
                thread.start_new_thread(getattr(self, 'onRawCTCP%s'%ctcpcmd),(sender, ctcpcmd, content))
            else:
                thread.start_new_thread(getattr(self, 'onRawCTCPDefault'),(sender, ctcpcmd, content))

            if hasattr(self.bot, 'onCTCP%s'%ctcpcmd):
                thread.start_new_thread(getattr(self.bot, 'onCTCP%s'%ctcpcmd),(sender, ctcpcmd, content))
            else:
                thread.start_new_thread(getattr(self.bot, 'onDefault'),(msg[0], cmd, ' '.join(msg[2:])))
