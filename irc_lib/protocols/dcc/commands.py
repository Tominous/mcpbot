import socket
import urllib

class DCCCommands(object):

    def rawcmd(self, target, cmd):
        self.out_msg.put(':%s PRIVMSG %s :\x01DCC %s\x01\r\n'%(self.cnick, target, cmd)) 

    def say(self, nick, msg):
        if not nick in self.sockets:return

        isGone = False
        while not isGone:
            try:
                self.sockets[nick].send(msg.strip()+'\r\n')
                isGone = True
            except socket.error:
                print 'Socket error !'
                raise socket.error

    def dcc(self, nick):
        target_ip = self.bot.getIP(nick)
        self.sockets[nick]      = None
        self.ip2nick[target_ip] = nick
        print target_ip, nick
        self.rawcmd(nick, 'CHAT chat %s %s'%(self.inip,self.inport))
