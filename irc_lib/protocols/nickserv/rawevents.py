from irc_lib.protocols.user import User


class NickServRawEvents(object):
    def onNSRV_ACC(self, ev):
        msg = ev.msg.split()
        if len(msg) < 3:
            self.logger.error('*** NSRV.onNSRV_ACC: INVALID: %s %s %s', ev.sender, ev.target, repr(ev.msg))
            return

        snick = msg[0]
        status = int(msg[2])

        self.locks['NSStatus'].acquire()
        if not snick in self.bot.users:
            self.bot.users[snick] = User(snick)
        self.bot.users[snick].status = status
        self.locks['NSStatus'].notifyAll()
        self.locks['NSStatus'].release()

    def onNSRV_Default(self, ev):
        self.logger.info('UNKNOWN NSRV EVENT: %s %s %s %s', ev.sender, ev.target, ev.cmd, repr(ev.msg))
