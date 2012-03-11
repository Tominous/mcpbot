import socket
import time
import logging
from threading import Condition
from Queue import Queue, Empty

from irc_lib.protocols.event import Event
from irc_lib.protocols.irc.protocol import IRCProtocol
from irc_lib.utils.ThreadPool import ThreadPool
from irc_lib.IRCBotError import IRCBotError
from irc_lib.IRCBotAdvMtd import IRCBotAdvMtd
from irc_lib.IRCBotIO import IRCBotIO


class IRCBotBase(IRCBotAdvMtd, IRCBotIO):
    """Base clase handling bot internal states and protocols.
    Provides a threadpool to handle bot commands, a user list updated as information become available,
    and access to all the procotols through self.<protocol> (irc, ctcp, dcc, and nickserv)"""

    def __init__(self, _nick='IRCBotLib', _char=':', _flood=1000, _dbconf='ircbot.sqlite'):
        self.log_config()
        self.logger = logging.getLogger('IRCBot')

        self.whitelist = {}

        self.controlchar = _char
        # Flood protection. Number of char / 30 secs (It is the way it works on esper.net)
        self.floodprotec = _flood

        self.cnick = _nick

        self.dbconf = _dbconf

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

        self.loggingq = Queue()
        self.commandq = Queue()

        # IRC Protocol handler
        self.irc = IRCProtocol(self.cnick, self.locks, self, self)
        self.nickserv = self.irc.nickserv
        self.ctcp = self.irc.ctcp
        self.dcc = self.irc.dcc

        # The basic IRC socket. For dcc, we are going to use another set of sockets.
        self.irc_socket = None

        self.irc_status = {'Server': None, 'Registered': False, 'Channels': set()}
        self.users = {}

        self.threadpool.add_task(self.logging_loop, _threadname='LoggingLoop')
        self.threadpool.add_task(self.command_loop, _threadname='CommandLoop')

    def log_config(self):
        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.WARN)

    def eventlog(self, ev):
        self.loggingq.put(ev)

    def command_loop(self):
        while not self.exit:
            try:
                ev = self.commandq.get(True, 1)
            except Empty:
                continue
            self.eventlog(ev)
            cmd_func = getattr(self, 'onCmd', self.onDefault)
            self.threadpool.add_task(cmd_func, ev)
            self.commandq.task_done()

    def process_msg(self, sender, target, msg):
        ischan = target[0] in ['#', '&']

        if ischan and msg[0] != self.controlchar:
            return

        if msg[0] == self.controlchar:
            msg = msg[1:]

        msg_split = msg.split(None, 1)
        outcmd = msg_split[0]
        if len(msg_split) > 1:
            outmsg = msg_split[1]
        else:
            outmsg = ''

        evcmd = Event(sender, outcmd, target, outmsg, 'CMD')
        self.commandq.put(evcmd)

    def connect(self, server, port=6667, password=None):
        """Connect to a server, handle authentification and start the communication threads."""
        if self.irc_socket:
            raise IRCBotError('Socket already existing, can not complete the connect command')
        self.logger.info('# Connecting to %s:%d', server, port)
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
                self.logger.error('EXIT REQUESTED. SHUTTING DOWN THE BOT')
                self.exit = True
        self.logger.info('*** IRCBotIO.start: exited')
        self.threadpool.wait_completion()
