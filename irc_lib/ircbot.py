import socket
import time
import logging
import re
import os
import pickle
import threading
from Queue import Queue, Empty

from irc_lib.event import Event
from irc_lib.user import User
from irc_lib.utils.ThreadPool import ThreadPool
from irc_lib.protocols.irc import IRCProtocol


LINESEP_REGEXP = re.compile(r'\r?\n')


class Error(Exception):
    pass


class IRCBotError(Error):
    pass


class IRCBotBase(object):
    """Base clase handling bot internal states and protocols.
    Provides a threadpool to handle bot commands, a user list updated as information become available,
    and access to all the procotols through self.<protocol> (irc, ctcp, dcc, and nickserv)"""

    def __init__(self, _nick='IRCBotLib', _char=':', _flood=1000, _log_level=logging.WARN):
        self.log_config(_log_level)
        self.logger = logging.getLogger('IRCBot')

        self.whitelist = {}

        self.controlchar = _char

        # Flood protection. Number of char / 30 secs (It is the way it works on esper.net)
        self.floodprotec = _flood

        self.cnick = _nick

        self.locks = {
            'ServReg': threading.Event(),
            'WhoIs': threading.Condition(),
            'NSID': threading.Event(),
            'NSStatus': threading.Condition()
        }

        self.exit = False

        self.nthreads = 10
        self.threadpool = ThreadPool(self.nthreads)

        # Outbound msgs
        self.out_msg = Queue()

        self.commandq = Queue()

        # IRC Protocol handler
        self.irc = IRCProtocol(self.cnick, self.locks, self, self)
        self.nickserv = self.irc.nickserv
        self.ctcp = self.irc.ctcp
        self.dcc = self.irc.dcc

        # The basic IRC socket. For dcc, we are going to use another set of sockets.
        self.irc_socket = None

        self.channels = set()
        self.users = {}

        self.threadpool.add_task(self.command_loop, _threadname='CommandLoop')

    def log_config(self, level=logging.WARN):
        logging.basicConfig(format='%(asctime)s %(message)s', level=level)

    def outbound_loop(self):
        """Outgoing messages thread. Check for new messages on the queue and push them to the socket if any."""
        # This is how the flood protection works :
        # We have a char bucket corresponding of the max number of chars per 30 seconds
        # Every looping, we add chars to this bucket corresponding to the time elapsed in the last loop * number of allowed char / second
        # If when we want to send the message and the number of chars is not enough, we sleep until we have enough chars in the bucket (in fact, a bit more, to replanish the bucket).
        # This way, everything slow down when we reach the flood limit, but after 30 seconds, the bucket is full again.

        try:
            allowed_chars = self.floodprotec
            start_time = time.time()
            while not self.exit:
                delta_time = time.time() - start_time
                allowed_chars = min(allowed_chars + (self.floodprotec / 30.0) * delta_time, self.floodprotec)
                start_time = time.time()

                if not self.irc_socket:
                    raise IRCBotError('no socket')

                try:
                    msg = self.out_msg.get(True, 1)
                except Empty:
                    continue

                self.logger.debug('> %s', repr(msg))
                out_line = msg + '\r\n'
                if len(out_line) > int(allowed_chars):
                    time.sleep((len(out_line) * 1.25) / (self.floodprotec / 30.0))
                try:
                    self.irc_socket.sendall(out_line)
                except socket.error:
                    self.out_msg.task_done()
                    raise
                allowed_chars -= len(out_line)
                self.out_msg.task_done()
        finally:
            self.logger.info('*** IRCBot.outbound_loop: exited')

    def inbound_loop(self):
        """Incoming message thread. Check for new data on the socket and send the data to the irc protocol handler."""
        try:
            buf = ''
            while not self.exit:
                if not self.irc_socket:
                    raise IRCBotError('no socket')

                # breaks with error: [Errno 104] Connection reset by peer
                try:
                    new_data = self.irc_socket.recv(512)
                except socket.timeout:
                    continue
                if not new_data:
                    raise IRCBotError('no data')

                msg_list = LINESEP_REGEXP.split(buf + new_data)

                # Push last line back into buffer in case its truncated
                buf = msg_list.pop()

                for msg in msg_list:
                    self.logger.debug('< %s', repr(msg))
                    self.irc.process_msg(msg)
        finally:
            self.logger.info('*** IRCBot.inbound_loop: exited')

    def command_loop(self):
        try:
            while not self.exit:
                try:
                    ev = self.commandq.get(True, 1)
                except Empty:
                    continue
                cmd_func = getattr(self, 'onCmd', self.onDefault)
                self.threadpool.add_task(cmd_func, ev)
                self.commandq.task_done()
        finally:
            self.logger.info('*** IRCBot.command_loop: exited')

    def process_msg(self, sender, target, msg):
        ischan = target[0] in ['#', '&']

        msg = msg.lstrip()

        if not msg:
            return

        if ischan and msg[0] != self.controlchar:
            return

        if msg[0] == self.controlchar:
            msg = msg[1:]

        msg_split = msg.split(None, 1)
        if not len(msg_split):
            return
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
        self.irc_socket.settimeout(5)

        self.threadpool.add_task(self.inbound_loop, _threadname='MainInLoop')
        self.threadpool.add_task(self.outbound_loop, _threadname='MainOutLoop')

        self.irc.password(password)
        self.irc.nick()
        self.irc.user()

        # wait until we are connected before returning
        self.locks['ServReg'].wait()

    def onDefault(self, ev):
        """Default event handler (do nothing)"""
        pass

    def getIP(self, nick):
        if nick not in self.users:
            self.users[nick] = User(nick)
        self.irc.whois(nick)
        with self.locks['WhoIs']:
            while self.users[nick].ip is None:
                self.locks['WhoIs'].wait()
        return self.users[nick].ip

    def getStatus(self, nick):
        if nick not in self.users:
            self.users[nick] = User(nick)
        if self.nickserv.online:
            self.nickserv.status(nick)
            with self.locks['NSStatus']:
                while self.users[nick].status is None:
                    self.locks['NSStatus'].wait()
        else:
            self.users[nick].status = 3
        return self.users[nick].status

    def rawcmd(self, msg):
        self.out_msg.put(msg)

    def say(self, nick, msg):
        if not msg:
            return
        # May have to come back here at some point if the users start holding their own socket
        if nick in self.dcc.sockets and self.dcc.sockets[nick]:
            self.dcc.say(nick, str(msg))
        elif nick[0] in ['#', '&']:
            self.irc.privmsg(nick, msg)
        else:
            self.irc.notice(nick, msg)

    def addWhitelist(self, nick, level=4):
        self.whitelist[nick] = level

    def rmWhitelist(self, nick):
        del self.whitelist[nick]

    def saveWhitelist(self, filename='whitelist.pck'):
        with open(filename, 'w') as ff:
            pickle.dump(self.whitelist, ff)

    def loadWhitelist(self, filename='whitelist.pck'):
        if os.path.isfile(filename):
            with open(filename, 'r') as ff:
                self.whitelist = pickle.load(ff)


    def start(self):
        """Start an infinite loop which can be exited by ctrl+c. Take care of cleaning the threads when exiting."""
        try:
            while not self.exit:
                try:
                    time.sleep(2)
                except (KeyboardInterrupt, SystemExit):
                    self.logger.error('EXIT REQUESTED. SHUTTING DOWN THE BOT')
                    self.exit = True
            self.threadpool.wait_completion()
        finally:
            self.logger.info('*** IRCBot.start: exited')
