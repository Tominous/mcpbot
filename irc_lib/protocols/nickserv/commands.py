class NickServCommands(object):

    def rawcmd(self, cmd):
        self.out_msg.put(':%s PRIVMSG NickServ :%s\r\n' % (self.cnick, cmd))

    def register(self):
        pass

    def identify(self, password):
        self.locks['ServReg'].acquire()
        while not self.bot.irc_status['Registered']:
            self.locks['ServReg'].wait()
        self.locks['ServReg'].release()

        self.rawcmd('IDENTIFY %s' % password)

    def drop(self):
        pass

    def auth(self):
        pass

    def sendauth(self):
        pass

    def reauth(self):
        pass

    def restoremail(self):
        pass

    def link(self):
        pass

    def unlink(self):
        pass

    def listlinks(self):
        pass

    def access(self):
        pass

    def set(self):
        pass

    def unset(self):
        pass

    def recover(self):
        pass

    def release(self):
        pass

    def ghost(self):
        pass

    def info(self):
        pass

    def listchans(self):
        pass

    def status(self, nick):
        self.rawcmd('ACC %s' % nick)  # Yeah, I know, this is not the right command, but they changed the nickserv on esper, and status doesn't returns the right value anymore :(
