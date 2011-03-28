import socket
import thread
import time, os
from sets import Set
from threading import Condition
from protocols.dispatcher import Dispatcher
from Queue import Queue,Empty
from IRCBotError import IRCBotError
from IRCBotAdvMtd import IRCBotAdvMtd
from utils.ThreadPool import ThreadPool

class IRCBotBase(IRCBotAdvMtd):
    """Base clase handling bot internal states and protocols.
    Provides a threadpool to handle bot commands, a user list updated as information become available,
    and access to all the procotols through self.<protocol> (irc, ctcp, dcc, and nickserv)"""
    
    whitelist = Set()
    
    def __init__(self, _nick='IRCBotLib', _char=':', _flood=1000):
        
        self.log         = None
        
        self.controlchar = _char
        self.floodprotec = _flood            #Flood protection. Number of char / 30 secs (It is the way it works on esper.net)
        
        self.cnick       = _nick
        
        self.rawmsg      = False
        
        self.locks           = {
            'WhoIs'    :Condition(),
            'ServReg'  :Condition(),
            'NSStatus' :Condition(),
        }


        self.localdic        = {}
        self.globaldic       = {'self':self}
        
        self.exit            = False
        
        self.threadpool      = ThreadPool(20)
        
        self.out_msg         = Queue()                                  #Outbound msgs
        self.in_msg          = Queue()                                  #Inbound msgs
        self.printq          = Queue()
        self.loggingq        = Queue()
        
        self.dispatcher      = Dispatcher(self.cnick, self.out_msg, self.in_msg, self.locks, self)  #IRC Protocol handler
        self.irc             = self.dispatcher.irc
        self.nickserv        = self.dispatcher.nse
        self.ctcp            = self.dispatcher.ctcp
        self.dcc             = self.dispatcher.dcc

        self.irc_socket      = None                                     #The basic IRC socket. For dcc, we are going to use another set of sockets.

        self.irc_status      = {'Server':None, 'Registered':False, 'Channels':Set()}
        self.users           = {}

        self.threadpool.add_task(self.print_loop)
        self.threadpool.add_task(self.logging_loop)

    def outbound_loop(self):
        """Outgoing messages thread. Check for new messages on the queue and push them to the socket if any."""
        #This is how the flood protection works :
        #We have a char bucket corresponding of the max number of chars per 30 seconds
        #Every looping, we add chars to this bucket corresponding to the time elapsed in the last loop * number of allowed char / second
        #If when we want to send the message and the number of chars is not enough, we sleep until we have enough chars in the bucket (in fact, a bit more, to replanish the bucket).
        #This way, everything slow down when we reach the flood limit, but after 30 seconds, the bucket is full again.
        
        allowed_chars = self.floodprotec
        start_time    = time.time()
        while not self.exit:
            delta_time = time.time() - start_time
            allowed_chars = min(allowed_chars + (self.floodprotec/30.0) * delta_time, self.floodprotec)
            start_time = time.time()
                        
            if not self.irc_socket : continue
            try:
                msg = self.out_msg.get(True, 1)
            except Empty:
                continue
            self.out_msg.task_done()
            if self.rawmsg:
                self.printq.put('> ' + msg.strip())
            if len(msg) > int(allowed_chars) : time.sleep((len(msg)*1.25)/(self.floodprotec/30.0))
            try:
                self.irc_socket.send(msg)
                allowed_chars -= len(msg)
            except socket.timeout:
                self.out_msg.put(msg)
                continue
                
            
    def inbound_loop(self):
        """Incoming message thread. Check for new data on the socket and push the data to the dispatcher queue if any."""
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
        """Loop to handle console output. Only way to have coherent output in a threaded environement.
        To output something to the console, just push it on the printq queue (self.printq.put('aaa') or self.bot.printq('aaa') from inside the procotols."""
        while not self.exit:
            try:
                msg = self.printq.get(True, 1)
            except Empty:
                continue
            self.printq.task_done()
            print msg

    def logging_loop(self):
        while not self.exit:
            try:
                ev = self.loggingq.get(True, 1)
            except Empty:
                continue            
            if self.log:            
                self.log.write('%s; %s; %s; %s; %s; %s\n'%(time.ctime(), ev.type.ljust(5), ev.cmd.ljust(15), ev.sender.ljust(20), ev.target.ljust(20), ev.msg))
                self.log.flush()        
                os.fsync(self.log.fileno())                


    def connect(self, server, port=6667):
        """Connect to a server, handle authentification and start the communication threads."""
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
        """Default event handler (do nothing)"""
        pass
        
    def start(self):
        """Start an infinite loop which can be exited by ctrl+c. Take care of cleaning the threads when exiting."""
        while not self.exit:
            try:
                time.sleep(2)
            except (KeyboardInterrupt, SystemExit):
                print 'EXIT REQUESTED. SHUTTING DOWN THE BOT'
                self.exit = True
                self.threadpool.wait_completion()
                if self.log: self.stopLogging()
                raise            
