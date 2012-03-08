import socket
import urllib
import select

from irc_lib.protocols.event import Event
from irc_lib.IRCBotIO import LINESEP_REGEXP
from commands import DCCCommands
from rawevents import DCCRawEvents


class DCCSocket(object):
    def __init__(self, _socket, _nick):
        self.buffer = ''
        self.socket = _socket
        self.nick = _nick

    def fileno(self):
        return self.socket.fileno()


class DCCProtocol(DCCCommands, DCCRawEvents):
    def __init__(self, _nick, _locks, _bot, _parent):
        self.cnick = _nick
        self.locks = _locks
        self.bot = _bot
        self.ctcp = _parent

        self.sockets = {}
        self.ip2nick = {}
        self.inip = None
        self.inport = None

        listenhost = ''
        listenport = 0
        self.insocket = socket.socket()
        try:
            self.insocket.bind((listenhost, listenport))
            self.insocket.listen(5)
            listenhost, listenport = self.insocket.getsockname()
        except socket.error as exc:
            self.log('*** DCC: insocket failed: %s' % exc)
            return

        externalip = urllib.urlopen('http://automation.whatismyip.com/n09230945.asp').readlines()[0]
        self.inip = self.conv_ip_std_long(externalip)
        self.inport = listenport

        self.log('DCC listening on %s:%d %s (%d %d)' % (listenhost, listenport, externalip, self.inip, self.inport))

        self.bot.threadpool.add_task(self.inbound_loop, _threadname='DCCInLoop')

    def log(self, msg):
        self.bot.log(msg)

    def eventlog(self, ev):
        self.bot.eventlog(ev)

    def process_msg(self, sender, target, msg):
        dcccmd, _, dccargs = msg.partition(' ')

        # regenerate event with parsed dcc details
        ev = Event(sender, dcccmd, target, dccargs, 'DCC')
        self.eventlog(ev)

        cmd_func = getattr(self, 'onDCC_%s' % dcccmd, self.onDCC_Default)
        cmd_func(ev)

        cmd_func = getattr(self.bot, 'onDCC_%s' % dcccmd, getattr(self.bot, 'onDCC_Default', self.bot.onDefault))
        cmd_func(ev)

    def process_DCCmsg(self, sender, msg):
        ev = Event(sender, 'DCCMSG', self.cnick, msg, 'DCCMSG')
        self.eventlog(ev)

        self.bot.threadpool.add_task(self.onRawDCCMsg, ev)

        cmd_func = getattr(self.bot, 'onDCCMsg', self.bot.onDefault)
        self.bot.threadpool.add_task(cmd_func, ev)

    def conv_ip_long_std(self, longip):
        try:
            ip = long(longip)
        except ValueError:
            self.log('*** DCC.conv_ip_long_std: invalid: %s' % repr(longip))
            return '0.0.0.0'
        if ip >= 2 ** 32:
            self.log('*** DCC.conv_ip_long_std: invalid: %s' % repr(longip))
            return '0.0.0.0'
        address = [str(ip >> shift & 0xFF) for shift in [24, 16, 8, 0]]
        return '.'.join(address)

    def conv_ip_std_long(self, stdip):
        address = stdip.split('.')
        if len(address) != 4:
            self.log('*** DCC.conv_ip_std_long: invalid: %s' % repr(stdip))
            return 0
        longip = 0
        for part, shift in zip(address, [24, 16, 8, 0]):
            try:
                ip_part = int(part)
            except ValueError:
                self.log('*** DCC.conv_ip_std_long: invalid: %s' % repr(stdip))
                return 0
            if ip_part >= 2 ** 8:
                self.log('*** DCC.conv_ip_std_long: invalid: %s' % repr(stdip))
                return 0
            longip += ip_part << shift
        return longip

    def inbound_loop(self):
        inp = [self.insocket]
        while not self.bot.exit:
            inputready, outputready, exceptready = select.select(inp, [], [], 5)

            for s in inputready:
                if s == self.insocket:
                    self.log('> Received connection request')
                    # handle the server socket
                    buffsocket, buffip = self.insocket.accept()
                    ip = buffip[0]
                    if ip in self.ip2nick:
                        nick = self.ip2nick[ip]
                        self.log('> User identified as: %s %s' % (nick, ip))
                        self.sockets[nick] = DCCSocket(buffsocket, nick)
                        self.say(nick, 'Connection with user %s established' % nick)
                        inp.append(self.sockets[nick])
                    else:
                        self.log('*** DCC.inbound_loop: connect from unknown ip: %s' % ip)
                else:
                    # handle all other sockets
                    try:
                        new_data = s.socket.recv(512)
                    except socket.error as exc:
                        if 'Connection reset by peer' in exc:
                            self.log('*** DCC.inbound_loop: connection closed: %s' % s.nick)
                            del self.sockets[s.nick]
                            s.socket.close()
                            inp.remove(s)
                        else:
                            self.log('*** DCC.inbound_loop: socket.error: %s %s' % (s.nick, exc))
                        continue
                    if not new_data:
                        self.log('*** DCC.inbound_loop: [No data] Connection closed: %s' % s.nick)
                        del self.sockets[s.nick]
                        s.socket.close()
                        inp.remove(s)
                        continue

                    msg_list = LINESEP_REGEXP.split(s.buffer + new_data)

                    # Push last line back into buffer in case its truncated
                    s.buffer = msg_list.pop()

                    for msg in msg_list:
                        if self.bot.rawmsg:
                            self.log('< %s' % repr(msg))
                        self.process_DCCmsg(s.nick, msg)
