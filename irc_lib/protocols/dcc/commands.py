import socket

from irc_lib.utils.colors import conv_s2i


class DCCCommands(object):
    def rawcmd(self, target, cmd):
        self.out_msg.put(':%s PRIVMSG %s :\x01DCC %s\x01' % (self.cnick, target, cmd))

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
                print 'Socket error !'
                raise
            except KeyError:
                print '[DCCCommands.say] Nick not found in socket table : %s' % nick

    def dcc(self, nick):
        target_ip = self.bot.getIP(nick)

        if nick in self.sockets and self.sockets[nick] is not None:
            self.sockets[nick].close()
            del self.sockets[nick]
        self.sockets[nick] = None

        self.ip2nick[target_ip] = nick
        self.rawcmd(nick, 'CHAT chat %s %s' % (self.inip, self.inport))
