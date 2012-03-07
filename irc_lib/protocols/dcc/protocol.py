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
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick = _nick
        self.out_msg = _out_msg
        self.in_msg = _in_msg
        self.bot = _bot
        self.locks = _locks

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

    def process_msg(self, ev):
        dcccmd, _, dccargs = ev.msg.partition(' ')

        # regenerate event with parsed dcc details
        ev = Event(ev.senderfull, dcccmd, ev.target, dccargs, 'DCC')
        self.bot.loggingq.put(ev)

        if hasattr(self, 'onDCC_%s' % dcccmd):
            self.bot.threadpool.add_task(getattr(self, 'onDCC_%s' % dcccmd), ev)
        else:
            self.bot.threadpool.add_task(getattr(self, 'onDCC_Default'), ev)

        if hasattr(self.bot, 'onDCC_%s' % dcccmd):
            self.bot.threadpool.add_task(getattr(self.bot, 'onDCC_%s' % dcccmd), ev)
        elif hasattr(self.bot, 'onDCC_Default'):
            self.bot.threadpool.add_task(getattr(self.bot, 'onDCC_Default'), ev)
        else:
            self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'), ev)

    def conv_ip_long_std(self, longip):
        hexip = hex(longip)[2:-1]
        if len(hexip) != 8:
            self.log('Error converting %d' % longip)
            return '0.0.0.0'
        part1 = int(hexip[0:2], 16)
        part2 = int(hexip[2:4], 16)
        part3 = int(hexip[4:6], 16)
        part4 = int(hexip[6:8], 16)
        ip = '%s.%s.%s.%s' % (part1, part2, part3, part4)
        return ip

    def conv_ip_std_long(self, stdip):
        ip = stdip.split('.')
        hexip = '%2s%2s%2s%2s' % (hex(int(ip[0]))[2:],
              hex(int(ip[1]))[2:],
              hex(int(ip[2]))[2:],
              hex(int(ip[3]))[2:])
        hexip = hexip.replace(' ', '0')
        longip = int(hexip, 16)
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

                            self.bot.loggingq.put(ev)

                            self.bot.threadpool.add_task(self.onRawDCCMsg, ev)
                            if hasattr(self.bot, 'onDCCMsg'):
                                self.bot.threadpool.add_task(self.bot.onDCCMsg, ev)
                            else:
                                self.bot.threadpool.add_task(self.bot.onDefault, ev)

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
