import socket
import urllib
import select
import sys
from Queue import Empty

from irc_lib.utils.irc_name import get_nick
from irc_lib.IRCBotError import IRCBotError
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

        self.insocket = socket.socket()
        try:
            self.insocket.listen(5)
            self.inip, self.inport = self.insocket.getsockname()
            self.inip = self.conv_ip_std_long(urllib.urlopen('http://automation.whatismyip.com/n09230945.asp').readlines()[0])
        except socket.error:
            self.log("DCC insocket failed")
            return

        self.bot.threadpool.add_task(self.treat_msg, _threadname='DCCHandler')
        self.bot.threadpool.add_task(self.inbound_loop, _threadname='DCCInLoop')

    def log(self, msg):
        self.bot.log(msg)

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

            sender = get_nick(msg[0])
            cmd = msg[1]
            destnick = msg[2]
            dcchead = msg[3][2:]
            dcccmd = msg[4]
            if len(msg) > 5:
                dccarg = msg[5]
                dccip = msg[6]
                dccport = msg[7][:-1]
            else:
                dccarg = ''
                dccip = ''
                dccport = ''

            if cmd not in ['PRIVMSG', 'NOTICE']:
                raise IRCBotError('Invalid command from DCC : %s' % msg)

            if hasattr(self, 'onRawDCC%s' % dcccmd):
                self.bot.threadpool.add_task(getattr(self, 'onRawDCC%s' % dcccmd), sender, dcccmd, dccarg, dccip, dccport)
            else:
                self.bot.threadpool.add_task(getattr(self, 'onRawDCCDefault'), sender, dcccmd, dccarg, dccip, dccport)

            if hasattr(self.bot, 'onDCC%s' % dcccmd):
                self.bot.threadpool.add_task(getattr(self.bot, 'onDCC%s' % dcccmd), sender, dcccmd, dccarg, dccip, dccport)
            else:
                self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'), msg[0], cmd, ' '.join(msg[2:]))

    def conv_ip_long_std(self, longip):
        hexip = hex(longip)[2:-1]
        if len(hexip) != 8:
            print 'Error !'
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

                        print r'>%s<' % s.buffer
                        if not s.buffer.strip():
                            s.buffer = ''
                            continue

                        msg_list = s.buffer.splitlines()

                        # We push all the msg beside the last one (in case it is truncated)
                        for msg in msg_list:
                            ev = Event(s.nick, 'DCCMSG', self.cnick, msg.strip(), self.cnick, 'DCCMSG')

                            self.log(ev)

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
                            print "========="
                            print "> Unexpected error while closing the socket :", sys.exc_info()[0]
                            print "========="
                            raise
