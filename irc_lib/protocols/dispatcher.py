from protocols.irc.protocol      import IRCProtocol
from protocols.nickserv.protocol import NickServProtocol
from protocols.ctcp.protocol     import CTCPProtocol
from protocols.dcc.protocol      import DCCProtocol
from utils.irc_name import get_nick
from Queue import Queue
import thread

class Dispatcher(object):
    
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):

        self.in_msg    = _in_msg

        self.irc_queue  = Queue()
        self.nse_queue  = Queue()
        self.ctcp_queue = Queue()
        self.dcc_queue  = Queue()
        
        self.irc  = IRCProtocol     (_nick, _out_msg, self.irc_queue,  _locks, _bot)
        self.nse  = NickServProtocol(_nick, _out_msg, self.nse_queue,  _locks, _bot)
        self.ctcp = CTCPProtocol    (_nick, _out_msg, self.ctcp_queue, _locks, _bot)        
        self.dcc  = DCCProtocol     (_nick, _out_msg, self.dcc_queue,  _locks, _bot)        

        thread.start_new_thread(self.treat_msg,  ())

    def treat_msg(self):
        while True:
            msg = self.in_msg.get()
            self.in_msg.task_done()

            sender = get_nick(msg.split()[0])
            cmd    = msg.split()[1]
            
            if sender.lower() == 'nickserv':
                self.nse_queue.put(msg)
            elif self.isCTCP(cmd, msg) and msg.split()[3][2:] == 'DCC':
                self.dcc_queue.put(msg)
            elif self.isCTCP(cmd, msg):
                self.ctcp_queue.put(msg)
            else:
                self.irc_queue.put(msg)

    def isCTCP(self, cmd, msg):
        if cmd in ['PRIVMSG', 'NOTICE'] and ' '.join(msg.split()[3:])[1] == '\x01' and ' '.join(msg.split()[3:])[-1] == '\x01': return True
        else: return False
