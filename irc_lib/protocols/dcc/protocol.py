import socket
import urllib
import select
import sys

from irc_lib.protocols.event import Event
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
    def __init__(self, _nick, _locks, _bot):
        self.cnick = _nick
        self.locks = _locks
        self.bot = _bot

        self.sockets = {}
        self.ip2nick = {}

        listenhost = ''
        listenport = 0
        self.insocket = socket.socket()
        try:
            self.insocket.bind((listenhost, listenport))
            self.insocket.listen(5)
            listenhost, listenport = self.insocket.getsockname()
        except socket.error:
            self.log("DCC insocket failed")
            raise

        externalip = urllib.urlopen('http://automation.whatismyip.com/n09230945.asp').readlines()[0]
        self.inip = self.conv_ip_std_long(externalip)
        self.inport = listenport

        self.log("DCC listening on %s:%d %s '%d %d'" % (listenhost, listenport, externalip, self.inip, self.inport))

        self.bot.threadpool.add_task(self.inbound_loop, _threadname='DCCInLoop')

    def log(self, msg):
        self.bot.log(msg)

    def eventlog(self, ev):
        self.bot.eventlog(ev)

    def process_msg(self, ev):
        dcccmd, _, dccargs = ev.msg.partition(' ')

        # regenerate event with parsed dcc details
        ev = Event(ev.senderfull, dcccmd, ev.target, dccargs, 'DCC')
        self.eventlog(ev)

        cmd_func = getattr(self, 'onDCC_%s' % dcccmd, self.onDCC_Default)
        cmd_func(ev)

        cmd_func = getattr(self.bot, 'onDCC_%s' % dcccmd, getattr(self.bot, 'onDCC_Default', self.bot.onDefault))
        cmd_func(ev)

    def conv_ip_long_std(self, longip):
        try:
            ip = long(longip)
        except ValueError:
            self.log("Invalid DCC IP '%s'" % longip)
            return '0.0.0.0'
        if ip >= 2 ** 32:
            self.log("Invalid DCC IP '%s'" % longip)
            return '0.0.0.0'
        address = [str(ip >> shift & 0xFF) for shift in [24, 16, 8, 0]]
        return '.'.join(address)

    def conv_ip_std_long(self, stdip):
        address = stdip.split('.')
        if len(address) != 4:
            self.log("Invalid IP '%s'" % stdip)
            return 0
        longip = 0
        for part, shift in zip(address, [24, 16, 8, 0]):
            try:
                ip_part = int(part)
            except ValueError:
                self.log("Invalid IP '%s'" % stdip)
                return 0
            if ip_part >= 2 ** 8:
                self.log("Invalid IP '%s'" % stdip)
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
                    if buffip[0] in self.ip2nick:
                        self.log('> User identified as : %s %s' % (self.ip2nick[buffip[0]], buffip[0]))
                        self.sockets[self.ip2nick[buffip[0]]] = DCCSocket(buffsocket, self.ip2nick[buffip[0]])
                        self.say(self.ip2nick[buffip[0]], 'Connection with user %s established.\r\n' % self.ip2nick[buffip[0]])
                        inp.append(self.sockets[self.ip2nick[buffip[0]]])
                    else:
                        # TODO: Check if something should be done here
                        pass
                else:
                    # handle all other sockets
                    data = None
                    try:
                        data = s.socket.recv(512)
                    except socket.error as msg:
                        if 'Connection reset by peer' in msg:
                            self.log('> [Connection reset] Connection closed with : %s' % s.nick)
                            del self.sockets[s.nick]
                            s.socket.close()
                            inp.remove(s)
                            continue
                    if data:
                        s.buffer += data

                        if self.bot.rawmsg:
                            self.log('< ' + s.buffer)

                        self.log(r'>%s<' % s.buffer)
                        if not s.buffer.strip():
                            s.buffer = ''
                            continue

                        msg_list = s.buffer.splitlines()

                        # We push all the msg beside the last one (in case it is truncated)
                        for msg in msg_list:
                            ev = Event(s.nick, 'DCCMSG', self.cnick, msg.strip(), 'DCCMSG')
                            self.eventlog(ev)

                            self.bot.threadpool.add_task(self.onRawDCCMsg, ev)

                            cmd_func = getattr(self.bot, 'onDCCMsg', self.bot.onDefault)
                            self.bot.threadpool.add_task(cmd_func, ev)

                        s.buffer = ''
                    else:
                        try:
                            self.log('> [No data] Connection closed with : %s' % s.nick)
                            del self.sockets[s.nick]
                            s.socket.close()
                            inp.remove(s)
                        except Exception:
                            # TODO : Specialized error handling. General except is BAD !
                            self.log("> Unexpected error while closing the socket: %s" % sys.exc_info()[0])
                            raise
