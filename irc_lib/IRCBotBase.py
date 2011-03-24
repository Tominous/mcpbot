import socket
import thread
import time
from sets import Set
from threading import Condition
from protocols.dispatcher import Dispatcher
from Queue import Queue,Empty
from IRCBotError import IRCBotError
from IRCBotAdvMtd import IRCBotAdvMtd
from utils.ThreadPool import ThreadPool

class IRCBotBase(IRCBotAdvMtd):
    
    def __init__(self, _nick='IRCBotLib', _char=':'):
        
        self.controlchar = _char
        
        self.cnick       = _nick
        
        self.locks           = {
            'WhoIs'    :Condition(),
            'ServReg'  :Condition(),
            'NSStatus' :Condition(),
        }
        
        self.exit            = False
        
        self.threadpool      = ThreadPool(20)
        
        self.out_msg         = Queue()                                  #Outbound msgs
        self.in_msg          = Queue()                                  #Inbound msgs
        self.printq          = Queue()
        
        self.dispatcher      = Dispatcher(self.cnick, self.out_msg, self.in_msg, self.locks, self)  #IRC Protocol handler
        self.irc             = self.dispatcher.irc
        self.nickserv        = self.dispatcher.nse
        self.ctcp            = self.dispatcher.ctcp
        self.dcc             = self.dispatcher.dcc

        self.irc_socket      = None                                     #The basic IRC socket. For dcc, we are going to use another set of sockets.

        self.irc_status      = {'Server':None, 'Registered':False, 'Channels':Set()}
        self.users           = {}

        self.threadpool.add_task(self.print_loop)

    def outbound_loop(self):
        while not self.exit:
            if not self.irc_socket : continue
            try:
                msg = self.out_msg.get(True, 1)
            except Empty:
                continue
            self.out_msg.task_done()
            try:
                self.irc_socket.send(msg)
            except socket.timeout:
                self.out_msg.put(msg)
                continue
            
    def inbound_loop(self):
        buffer = ''
        while not self.exit:
            if not self.irc_socket : continue

            try:
                buffer  += self.irc_socket.recv(512)
            except socket.timeout:
                continue
            msg_list = buffer.split('\r\n')

            #We push all the msg beside the last one (in case it is truncated)
            for msg in msg_list[:-1]:
                self.in_msg.put(msg.replace('\r\n',''))
            
            #If the last message is truncated, we push it back in the buffer. Else, we push it on the queue and clear the buffer.
            if msg_list[-1][-2:] != '\r\n':
                buffer = msg_list[-1]
            else:
                self.in_msg.put(msg_list[-1])
                buffer = ''        

    def print_loop(self):
        while not self.exit:
            try:
                msg = self.printq.get(True, 1)
            except Empty:
                continue
            self.printq.task_done()
            print msg

    def connect(self, server, port=6667):
        if self.irc_socket : raise IRCBotError('Socket already existing, can not complete the connect command')
        self.irc_socket = socket.socket()
        self.irc_socket.connect((server, port))
        self.irc_socket.settimeout(1)

        self.irc.password()
        self.irc.nick()
        self.irc.user()
        self.threadpool.add_task(self.inbound_loop)
        self.threadpool.add_task(self.outbound_loop)

    def onDefault(self, sender, cmd, msg):
        pass
        
    def start(self):
        while not self.exit:
            try:
                time.sleep(2)
            except (KeyboardInterrupt, SystemExit):
                print 'EXIT REQUESTED. SHUTTING DOWN THE BOT'
                self.exit = True
                self.threadpool.wait_completion()
                raise            
