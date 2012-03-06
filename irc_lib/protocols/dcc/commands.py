import socket

from irc_lib.utils.colors import conv_s2i


class DCCCommands(object):
    def dcc_privmsg(self, target, cmd, args):
        msg = cmd + ' ' + args
        self.bot.ctcp.ctcp_privmsg(target, 'DCC', msg)

    def dcc_notice(self, target, cmd, args):
        msg = cmd + ' ' + args
        self.bot.ctcp.ctcp_notice(target, 'DCC', msg)

    def say(self, nick, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        if not nick in self.sockets:
            return

        isGone = False
        while not isGone:
            try:
                self.sockets[nick].socket.send(msg.strip() + '\r\n')
                isGone = True
            except socket.error:
                self.log('Socket error !')
                raise
            except KeyError:
                self.log('[DCCCommands.say] Nick not found in socket table : %s' % nick)

    def dcc(self, nick):
        target_ip = self.bot.getIP(nick)

        if nick in self.sockets and self.sockets[nick] is not None:
            self.sockets[nick].close()
            del self.sockets[nick]
        self.sockets[nick] = None

        self.ip2nick[target_ip] = nick
        self.dcc_privmsg(nick, 'CHAT', 'CHAT %s %s' % (self.inip, self.inport))
