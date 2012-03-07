import socket
import time
from threading import Condition
from Queue import Queue, Empty

from irc_lib.protocols.irc.protocol import IRCProtocol
from irc_lib.protocols.nickserv.protocol import NickServProtocol
from irc_lib.protocols.ctcp.protocol import CTCPProtocol
from irc_lib.protocols.dcc.protocol import DCCProtocol
from utils.ThreadPool import ThreadPool
from IRCBotError import IRCBotError
from IRCBotAdvMtd import IRCBotAdvMtd
from IRCBotIO import IRCBotIO


class IRCBotBase(IRCBotAdvMtd, IRCBotIO):
    """Base clase handling bot internal states and protocols.
    Provides a threadpool to handle bot commands, a user list updated as information become available,
    and access to all the procotols through self.<protocol> (irc, ctcp, dcc, and nickserv)"""

    def __init__(self, _nick='IRCBotLib', _char=':', _flood=1000, _dbconf='ircbot.sqlite'):
        self.whitelist = {}

        self.controlchar = _char
        # Flood protection. Number of char / 30 secs (It is the way it works on esper.net)
        self.floodprotec = _flood

        self.cnick = _nick

        self.dbconf = _dbconf

        self.rawmsg = False

        self.locks = {
            'WhoIs': Condition(),
            'ServReg': Condition(),
            'NSStatus': Condition()
        }

        self.localdic = {}
        self.globaldic = {'self': self}

        self.exit = False

        self.nthreads = 15
        self.threadpool = ThreadPool(self.nthreads)

        # Outbound msgs
        self.out_msg = Queue()

        self.printq = Queue()
        self.loggingq = Queue()
        self.commandq = Queue()

        # IRC Protocol handler
        self.irc = IRCProtocol(self.cnick, self.locks, self)
        self.nickserv = NickServProtocol(self.cnick, self.locks, self)
        self.ctcp = CTCPProtocol(self.cnick, self.locks, self)
        self.dcc = DCCProtocol(self.cnick, self.locks, self)

        # The basic IRC socket. For dcc, we are going to use another set of sockets.
        self.irc_socket = None

        self.irc_status = {'Server': None, 'Registered': False, 'Channels': set()}
        self.users = {}

        self.threadpool.add_task(self.print_loop, _threadname='PrintLoop')
        self.threadpool.add_task(self.logging_loop, _threadname='LoggingLoop')
        self.threadpool.add_task(self.command_loop, _threadname='CommandLoop')

    def log(self, msg):
        self.printq.put(msg)

    def command_loop(self):
        while not self.exit:
            try:
                msg = self.commandq.get(True, 1)
            except Empty:
                continue
            self.commandq.task_done()

            self.loggingq.put(msg)

            cmd_func = getattr(self, 'onCmd', self.onDefault)
            self.threadpool.add_task(cmd_func, msg)

    def connect(self, server, port=6667, password=None):
        """Connect to a server, handle authentification and start the communication threads."""
        if self.irc_socket:
            raise IRCBotError('Socket already existing, can not complete the connect command')
        self.irc_socket = socket.socket()
        self.irc_socket.connect((server, port))
        self.irc_socket.settimeout(1)

        self.irc.password(password)
        self.irc.nick()
        self.irc.user()

        self.threadpool.add_task(self.inbound_loop, _threadname='MainInLoop')
        self.threadpool.add_task(self.outbound_loop, _threadname='MainOutLoop')

    def onDefault(self, ev):
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
                raise
