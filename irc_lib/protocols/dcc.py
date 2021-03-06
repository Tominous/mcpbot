import socket
import urllib
import select

from irc_lib.event import Event
from irc_lib.utils.colors import conv_s2i
from irc_lib.protocol import Protocol
import irc_lib.ircbot


class DCCSocket(object):
    def __init__(self, socket_, nick):
        self.buffer = ''
        self.socket = socket_
        self.nick = nick

    def fileno(self):
        return self.socket.fileno()


class DCCProtocol(Protocol):
    def __init__(self, nick, locks, bot, parent):
        Protocol.__init__(self, nick, locks, bot, parent, 'IRCBot.DCC')
        self.ctcp = self.parent

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
        except socket.error:
            self.logger.exception('*** DCC: bind insocket failed')
            return
        externalip = urllib.urlopen('http://ifconfig.me/ip').readlines()[0]
        self.inip = self.conv_ip_std_long(externalip)
        self.inport = listenport
        self.logger.info('# DCC listening on %s:%d %s', listenhost, listenport, externalip)

        self.bot.threadpool.add_task(self.inbound_loop, threadname='DCCInLoop')

    def process_msg(self, sender, target, msg):
        dcccmd, _, dccargs = msg.partition(' ')

        # regenerate event with parsed dcc details
        evt = Event(sender, dcccmd, target, dccargs, 'DCC')

        cmd_func = getattr(self, 'onDCC_%s' % dcccmd, self.onDCC_default)
        cmd_func(evt)

        cmd_func = getattr(self.bot, 'onDCC_%s' % dcccmd, getattr(self.bot, 'onDCC_default', self.bot.on_default))
        cmd_func(evt)

    def process_DCCmsg(self, sender, msg):
        evt = Event(sender, 'DCCMSG', self.cnick, msg, 'DCC', dcc=True)

        self.bot.threadpool.add_task(self.onDCC_msg, evt)

        cmd_func = getattr(self.bot, 'onDCC_msg', self.bot.on_default)
        self.bot.threadpool.add_task(cmd_func, evt)

    def conv_ip_long_std(self, longip):
        try:
            ip = long(longip)
        except ValueError:
            self.logger.error('*** DCC.conv_ip_long_std: invalid: %s', repr(longip))
            return '0.0.0.0'
        if ip >= 2 ** 32:
            self.logger.error('*** DCC.conv_ip_long_std: invalid: %s', repr(longip))
            return '0.0.0.0'
        address = [str(ip >> shift & 0xFF) for shift in [24, 16, 8, 0]]
        return '.'.join(address)

    def conv_ip_std_long(self, stdip):
        address = stdip.split('.')
        if len(address) != 4:
            self.logger.error('*** DCC.conv_ip_std_long: invalid: %s', repr(stdip))
            return 0
        longip = 0
        for part, shift in zip(address, [24, 16, 8, 0]):
            try:
                ip_part = int(part)
            except ValueError:
                self.logger.error('*** DCC.conv_ip_std_long: invalid: %s', repr(stdip))
                return 0
            if ip_part >= 2 ** 8:
                self.logger.error('*** DCC.conv_ip_std_long: invalid: %s', repr(stdip))
                return 0
            longip += ip_part << shift
        return longip

    def inbound_loop(self):
        inp = [self.insocket]
        while not self.bot.exit:
            inputready, _, _ = select.select(inp, [], [], 5)

            for skt in inputready:
                if skt == self.insocket:
                    self.logger.info('# Received connection request')
                    # handle the server socket
                    buffsocket, buffip = self.insocket.accept()
                    ip = buffip[0]
                    if ip in self.ip2nick:
                        nick = self.ip2nick[ip]
                        self.logger.info('# User identified as: %s %s', nick, ip)
                        self.sockets[nick] = DCCSocket(buffsocket, nick)
                        self.say(nick, 'Connection with user %s established' % nick)
                        inp.append(self.sockets[nick])
                    else:
                        self.logger.warn('*** DCC.inbound_loop: connect from unknown ip: %s', ip)
                else:
                    # handle all other sockets
                    new_data = None
                    close_socket = False
                    try:
                        new_data = skt.socket.recv(512)
                    except socket.timeout:
                        self.logger.info('*** DCC.inbound_loop: Connection closed [timeout]: %s', skt.nick)
                        close_socket = True
                    except socket.error as exc:
                        if 'Connection reset by peer' in exc:
                            self.logger.info('*** DCC.inbound_loop: Connection closed [reset]: %s', skt.nick)
                        elif 'Connection timed out' in exc:
                            self.logger.info('*** DCC.inbound_loop: Connection closed [timeout]: %s', skt.nick)
                        else:
                            self.logger.exception('*** DCC.inbound_loop: Connection closed [error]: %s', skt.nick)
                        close_socket = True
                    if not close_socket and not new_data:
                        self.logger.info('*** DCC.inbound_loop: Connection closed [no data]: %s', skt.nick)
                        close_socket = True
                    if close_socket:
                        if skt.nick in self.sockets:
                            del self.sockets[skt.nick]
                        else:
                            self.logger.info('*** DCC.inbound_loop: not in sockets: %s', skt.nick)
                        skt.socket.close()
                        inp.remove(skt)
                        continue

                    msg_list = irc_lib.ircbot.LINESEP_REGEXP.split(skt.buffer + new_data)

                    # Push last line back into buffer in case its truncated
                    skt.buffer = msg_list.pop()

                    for msg in msg_list:
                        self.logger.debug('< %s %s', skt.nick, repr(msg))
                        self.process_DCCmsg(skt.nick, msg)
        self.logger.info('*** DCC.inbound_loop: exited')

    def onDCC_msg(self, evt):
        self.bot.process_msg(evt.sender, self.cnick, evt.msg, dcc=evt.dcc)

    def onDCC_CHAT(self, evt):
        nick = evt.sender
        args = evt.msg.split()
        if len(args) != 3:
            self.logger.error('*** DCC.onDCC_CHAT: INVALID: %s %s %s', evt.sender, evt.target, repr(evt.msg))
            return
        dccprot = args[0]
        dccip = self.conv_ip_long_std(args[1])
        dccport = int(args[2])

        self.logger.info('onDCC_CHAT: %s %s | IP:%s Port:%s', evt.sender, repr(evt.msg), dccip, dccport)

    def onDCC_default(self, evt):
        self.logger.info('RAW DCC EVENT: %s %s %s %s', evt.sender, evt.target, evt.cmd, repr(evt.msg))

    def dcc_privmsg(self, target, cmd, args):
        msg = cmd + ' ' + args
        self.ctcp.ctcp_privmsg(target, 'DCC', msg)

    def dcc_notice(self, target, cmd, args):
        msg = cmd + ' ' + args
        self.ctcp.ctcp_notice(target, 'DCC', msg)

    def say(self, nick, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        if nick not in self.sockets:
            self.logger.error('*** DCC.say: unknown nick: %s', nick)
            return

        self.logger.debug('> %s %s', nick, repr(msg))
        out_line = msg + '\r\n'
        try:
            self.sockets[nick].socket.sendall(out_line)
        except socket.error:
            self.logger.exception('*** DCC.say: socket.error: %s', nick)
            return
        except KeyError:
            self.logger.error('*** DCC.say: unknown nick: %s', nick)
            return

    def dcc(self, nick):
        if not self.inip:
            self.bot.say(nick, '$BDCC currently disabled')
            return

        target_ip = self.bot.get_ip(nick)

        if nick in self.sockets and self.sockets[nick] is not None:
            self.logger.warn('*** DCC.dcc: already connected: %s', nick)
            # this is breaking the select loop in inbound_loop
            del self.sockets[nick]
        self.sockets[nick] = None

        self.ip2nick[target_ip] = nick
        self.dcc_privmsg(nick, 'CHAT', 'CHAT %s %s' % (self.inip, self.inport))
