from irc_lib.event import Event
from irc_lib.user import User
from irc_lib.protocol import Protocol


NICKSERV = 'NickServ'


class NickServProtocol(Protocol):
    def __init__(self, nick, locks, bot, parent):
        Protocol.__init__(self, nick, locks, bot, parent, 'IRCBot.NSRV')
        self.irc = self.parent
        self.online = False
        self.identified = False

    def process_msg(self, prefix, target, msg):
        split_msg = msg.split()
        if len(split_msg) > 1 and split_msg[1] in ['ACC']:
            cmd = split_msg[1]
        elif msg.startswith('This nickname is registered'):
            cmd = 'NEED_ID'
        elif msg.startswith('You are now identified'):
            cmd = 'ID_DONE'
        elif msg.startswith('Invalid password'):
            cmd = 'ERR_PASS'
        elif msg.startswith('Last failed attempt from'):
            cmd = 'ERR_LASTFAIL'
        elif msg.endswith('since last login.'):
            cmd = 'ERR_FAILCNT'
        else:
            cmd = 'Unknown'

        evt = Event(prefix, cmd, target, msg, 'NSRV')

        cmd_func = getattr(self, 'onNSRV_%s' % evt.cmd, self.onNSRV_default)
        cmd_func(evt)

        cmd_func = getattr(self.bot, 'onNSRV_%s' % evt.cmd, getattr(self.bot, 'onNSRV_default', self.bot.on_default))
        cmd_func(evt)

    def onNSRV_NEED_ID(self, evt):
        pass

    def onNSRV_ID_DONE(self, evt):
        # logged in successfully
        self.online = True
        self.identified = True
        self.locks['NSID'].set()

    def onNSRV_ERR_PASS(self, evt):
        # bad password
        self.logger.warning('*** Bad %s password for %s', NICKSERV, self.cnick)
        self.online = True
        self.locks['NSID'].set()

    def onNSRV_ERR_LASTFAIL(self, evt):
        self.logger.warning('*** %s %s', NICKSERV, evt.msg.replace('\x02', ''))

    def onNSRV_ERR_FAILCNT(self, evt):
        self.logger.warning('*** %s %s', NICKSERV, evt.msg.replace('\x02', ''))

    def onNSRV_ACC(self, evt):
        msg = evt.msg.split()
        if len(msg) < 3:
            self.logger.error('*** NSRV.onNSRV_ACC: INVALID: %s %s %s', evt.sender, evt.target, repr(evt.msg))
            return

        snick = msg[0]
        status = int(msg[2])

        with self.locks['NSStatus']:
            if snick not in self.bot.users:
                self.bot.users[snick] = User(snick)
            self.bot.users[snick].status = status
            self.locks['NSStatus'].notifyAll()

    def onNSRV_default(self, evt):
        self.logger.info('UNKNOWN NSRV EVENT: %s %s %s %s', evt.sender, evt.target, evt.cmd, repr(evt.msg))

    def nserv_privmsg(self, msg):
        self.irc.privmsg(NICKSERV, msg, color=False)

    def nserv_notice(self, msg):
        self.irc.notice(NICKSERV, msg, color=False)

    def identify(self, password):
        # identify to nickserv, we don't return until we get a response from the server
        self.nserv_privmsg('IDENTIFY %s' % password)
        self.locks['NSID'].wait()

    def no_nickserv(self):
        # called if there is no NickServ online
        self.logger.warning('*** %s not online', NICKSERV)
        self.locks['NSID'].set()

    def status(self, nick):
        # Yeah, I know, this is not the right command, but they changed the nickserv on esper, and status doesn't returns the right value anymore :(
        self.nserv_privmsg('ACC %s' % nick)

    def ghost(self, nick, password):
        self.nserv_privmsg('GHOST %s %s' % (nick, password))
