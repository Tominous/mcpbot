from commands  import IRCCommands
from rawevents import IRCRawEvents
from constants import IRC_REPLIES
import thread
from threading import Condition
import time

class IRCProtocol(IRCCommands, IRCRawEvents):
    
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
            
            try:
                msg[1] = IRC_REPLIES.get(int(msg[1]), 'UNKNOWN')
            except ValueError:
                pass
            
            if msg[0] == 'PING':
                self.onRawPING(msg)
                if hasattr(self.bot, 'onPING'):
                    self.bot.onPING(msg)
            else:
                sender = msg[0][1:]
                cmd    = msg[1]
                msg    = ' '.join(msg[2:])
                if hasattr(self, 'onRaw%s'%cmd):
                    thread.start_new_thread(getattr(self, 'onRaw%s'%cmd),(sender, cmd, msg))
                else:
                    thread.start_new_thread(getattr(self, 'onRawDefault'),(sender, cmd, msg))

                if hasattr(self.bot, 'on%s'%cmd):
                    thread.start_new_thread(getattr(self.bot, 'on%s'%cmd),(sender, cmd, msg))
                else:
                    thread.start_new_thread(getattr(self.bot, 'onDefault'),(sender, cmd, msg))
                
    def add_user(self, nick, chan):
        nick_status = '-'
        snick = nick
        if nick[0] in ['@', '+']:
            snick = nick[1:]
            nick_status = nick[0]
        if not snick in self.bot.irc_status['Users']:
            self.bot.irc_status['Users'][snick] = {}
            self.bot.irc_status['Users'][snick]['Registered'] = -1
            self.bot.irc_status['Users'][snick]['Host'] = -1
            self.bot.irc_status['Users'][snick]['IP']   = -1
        self.bot.irc_status['Users'][snick]['Channels'] = {}
        self.bot.irc_status['Users'][snick]['Channels'][chan] = nick_status        
    
    def rm_user(self, nick, chan=None):
        if not chan:
            del self.bot.irc_status['Users'][nick]
            return
            
        del self.bot.irc_status['Users'][nick]['Channels'][chan]
        if len(self.bot.irc_status['Users'][nick]['Channels']) == 0:
            del self.bot.irc_status['Users'][nick]


