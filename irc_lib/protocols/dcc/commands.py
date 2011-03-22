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
                print 'Error !'
                raise socket.error

    def dcc(self, nick):
        whatismyip = 'http://www.whatismyip.com/automation/n09230945.asp'
        myip = urllib.urlopen(whatismyip).readlines()[0]        
    
        self.listeningsocks[nick] = socket.socket()
        self.listeningsocks[nick].listen(5)
        self.listeningsocks[nick].setblocking(0)
        addr,port = self.listeningsocks[nick].getsockname()
        
        ircip = self.conv_ip_std_long(myip)

        self.rawcmd(nick, 'CHAT chat %s %s'%(ircip,port))
