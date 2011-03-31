from irc_lib.utils.irc_name import get_nick
from commands  import CTCPCommands
from rawevents import CTCPRawEvents
from irc_lib.IRCBotError import IRCBotError
from irc_lib.protocols.event import Event
from Queue import Queue,Empty
import thread
import time

class CTCPProtocol(CTCPCommands, CTCPRawEvents):

    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick           = _nick
        self.out_msg         = _out_msg
        self.in_msg          = _in_msg
        self.bot             = _bot
        self.locks           = _locks
        
        self.bot.threadpool.add_task(self.treat_msg, _threadname='CTCPHandler')
        #thread.start_new_thread(self.treat_msg,  ())

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
            msg[3] = ' '.join(msg[3:])
            msg    = msg[:4]
            msg[3] = msg[3].replace('\x01','') #We remove the leading/tailing \x01
            
            if len(msg[3].split()) < 2: outmsg = ' '
            else: outmsg = ' '.join(msg[3].split()[1:])
            
            ev = Event(msg[0], msg[3].split()[0][1:], msg[2], outmsg, self.cnick, 'CTCP')
            
            if hasattr(self, 'onRawCTCP%s'%ev.cmd):
                self.bot.threadpool.add_task(getattr(self, 'onRawCTCP%s'%ev.cmd), ev)
            else:
                self.bot.threadpool.add_task(getattr(self, 'onRawCTCPDefault'),ev)

            if hasattr(self.bot, 'onCTCP%s'%ev.cmd):
                self.bot.threadpool.add_task(getattr(self.bot, 'onCTCP%s'%ev.cmd),ev)
            else:
                self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'),ev)
