import time

class CTCPCommands(object):

    def rawcmd(self, target, cmd):
        self.out_msg.put(':%s PRIVMSG %s :\x01%s\x01\r\n'%(self.cnick, target, cmd))

    def rawnotice(self, target, cmd):
        self.out_msg.put(':%s NOTICE %s :\x01%s\x01\r\n'%(self.cnick, target, cmd))

    def time(self, target):
        self.rawcmd(target, 'TIME')

    def action(self, channel, text):
        self.rawcmd(channel, 'ACTION %s'%text)

    def finger(self, target):
        self.rawcmd(target, 'FINGER')

    def version():
        self.rawcmd(target, 'VERSION')

    def source():
        self.rawcmd(target, 'SOURCE')

    def userinfo():
        self.rawcmd(target, 'USERINFO')

    def clientinfo():
        self.rawcmd(target, 'CLIENTINFO')

    def errmsg(self):
        pass

    def ping(self, target):
        self.rawcmd(target, 'CLIENTINFO %s'%time.time())
