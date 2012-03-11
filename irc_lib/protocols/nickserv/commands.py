from irc_lib.protocols.nickserv.constants import NICKSERV


class NickServCommands(object):
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
