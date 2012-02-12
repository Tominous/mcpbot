from irc_lib.protocols.user import User


class NickServRawEvents(object):


    def onRawNickServACC(self, ev):
        if not ev.msg:
            return
        self.bot.printq.put(ev.msg)
        snick = ev.msg.split()[0]
        status = ev.msg.split()[1]

        self.locks['NSStatus'].acquire()
        if not snick in self.bot.users:
            self.bot.users[nick] = User(nick)
        self.bot.users[snick].status = int(status)
        self.locks['NSStatus'].notifyAll()
        self.locks['NSStatus'].release()

    def onRawNickServDefault(self, ev):
        pass
