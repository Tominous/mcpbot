import logging

from irc_lib.event import Event
from irc_lib.user import User


NICKSERV = 'NickServ'


class NickServProtocol(object):
    def __init__(self, _nick, _locks, _bot, _parent):
        self.logger = logging.getLogger('IRCBot.NSRV')
        self.cnick = _nick
        self.locks = _locks
        self.bot = _bot
        self.irc = _parent

    def process_msg(self, prefix, target, msg):
        split_msg = msg.split()
        if len(split_msg) > 1 and split_msg[1] in ['ACC']:
            cmd = split_msg[1]
        else:
            cmd = 'Unknown'

        ev = Event(prefix, cmd, target, msg, 'NSRV')

        cmd_func = getattr(self, 'onNSRV_%s' % ev.cmd, self.onNSRV_Default)
        cmd_func(ev)

        cmd_func = getattr(self.bot, 'onNSRV_%s' % ev.cmd, getattr(self.bot, 'onNSRV_Default', self.bot.onDefault))
        cmd_func(ev)

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

    def nserv_privmsg(self, msg):
        self.irc.privmsg(NICKSERV, msg, color=False)

    def nserv_notice(self, msg):
        self.irc.notice(NICKSERV, msg, color=False)

    def identify(self, password):
        self.locks['ServReg'].acquire()
        while not self.bot.irc_status['Registered']:
            self.locks['ServReg'].wait()
        self.locks['ServReg'].release()

        self.nserv_privmsg('IDENTIFY %s' % password)

    def status(self, nick):
        # Yeah, I know, this is not the right command, but they changed the nickserv on esper, and status doesn't returns the right value anymore :(
        self.nserv_privmsg('ACC %s' % nick)
