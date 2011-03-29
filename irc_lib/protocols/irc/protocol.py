from commands  import IRCCommands
from rawevents import IRCRawEvents
from constants import IRC_REPLIES
import thread
from threading import Condition
from irc_lib.protocols.event import Event
from irc_lib.protocols.user import User
from Queue import Queue,Empty
import time

class IRCProtocol(IRCCommands, IRCRawEvents):
    
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick           = _nick
        self.out_msg         = _out_msg
        self.in_msg          = _in_msg
        self.bot             = _bot
        self.locks           = _locks

        self.bot.threadpool.add_task(self.treat_msg)        

    def treat_msg(self):
        while not self.bot.exit:
            try:
                msg = self.in_msg.get(True, 1)
            except Empty:
                continue  
            self.in_msg.task_done()
            
            msg = msg.strip()
            if not msg:
                continue
            
            msg = msg.split()
            
            try:
                msg[1] = IRC_REPLIES.get(int(msg[1]), 'UNKNOWN_%d'%int(msg[1]))
            except ValueError:
                pass
            
            if msg[0] == 'PING':
                self.onRawPING(msg)
                if hasattr(self.bot, 'onPING'):
                    self.bot.onPING(msg)
            else:
                if len(msg) < 4 : msg.append(' ')
                ev = Event(msg[0], msg[1], msg[2], ' '.join(msg[3:]), self.cnick, 'IRC')

                if hasattr(self, 'onRaw%s'%ev.cmd):
                    self.bot.threadpool.add_task(getattr(self, 'onRaw%s'%ev.cmd),ev)
                else:
                    self.bot.threadpool.add_task(getattr(self, 'onRawDefault'),ev)

                if hasattr(self.bot, 'on%s'%ev.cmd):
                    self.bot.threadpool.add_task(getattr(self.bot, 'on%s'%ev.cmd),ev)
                else:
                    self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'),ev)
                
    def add_user(self, nick, chan=None):
        nick_status = '-'
        snick = nick
        if nick[0] in ['@', '+']:
            snick = nick[1:]
            nick_status = nick[0]

        if not snick in self.bot.users: self.bot.users[snick] = User(snick)
        if not chan: return
        self.bot.users[snick].chans[chan] = nick_status
    
    def rm_user(self, nick, chan=None):
        if not nick in self.bot.users:
            print 'WARNING : Tried to remove an inexisting user : %s.'%nick
            return
        
        if not chan:
            del self.bot.users[nick]
            return
            
        del self.bot.users[nick].chans[chan]
        if len(self.bot.users[nick].chans) == 0:
            del self.bot.users[nick]


#DEAD CODE ZONE
