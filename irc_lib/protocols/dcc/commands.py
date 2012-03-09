import socket

from irc_lib.utils.colors import conv_s2i


class DCCCommands(object):
    def dcc_privmsg(self, target, cmd, args):
        msg = cmd + ' ' + args
        self.ctcp.ctcp_privmsg(target, 'DCC', msg)

    def dcc_notice(self, target, cmd, args):
        msg = cmd + ' ' + args
        self.ctcp.ctcp_notice(target, 'DCC', msg)

    def say(self, nick, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        if not nick in self.sockets:
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

        target_ip = self.bot.getIP(nick)

        if nick in self.sockets and self.sockets[nick] is not None:
            self.logger.warn('*** DCC.dcc: already connected: %s', nick)
            # this is breaking the select loop in inbound_loop
            del self.sockets[nick]
        self.sockets[nick] = None

        self.ip2nick[target_ip] = nick
        self.dcc_privmsg(nick, 'CHAT', 'CHAT %s %s' % (self.inip, self.inport))
