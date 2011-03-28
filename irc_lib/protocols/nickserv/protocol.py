from irc_lib.utils.irc_name import get_nick
from commands  import NickServCommands
from rawevents import NickServRawEvents
from irc_lib.IRCBotError import IRCBotError
from irc_lib.protocols.event import Event
from threading import Condition
from Queue import Queue,Empty
import thread
import time

class NickServProtocol(NickServCommands, NickServRawEvents):

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

            if self.bot.rawmsg:
                self.bot.printq.put('< ' + msg)
                
            msg = msg.split()

            if len(msg) < 5 : msg.append(' ')
            ev = Event(msg[0], msg[4], msg[2], ' '.join([msg[3], msg[5]]), self.cnick, 'NSERV')

    #def __init__(self, sender, cmd, target, msg, selfnick, etype):
                
                
            if hasattr(self, 'onRawNickServ%s'%ev.cmd):
                self.bot.threadpool.add_task(getattr(self, 'onRawNickServ%s'%ev.cmd),ev)
            else:
                self.bot.threadpool.add_task(getattr(self, 'onRawNickServDefault'),ev)

            if hasattr(self.bot, 'onNickServ%s'%ev.cmd):
                self.bot.threadpool.add_task(getattr(self.bot, 'onNickServ%s'%ev.cmd),ev)
            else:
                self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'),ev)


