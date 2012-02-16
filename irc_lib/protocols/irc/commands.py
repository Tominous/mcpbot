from irc_lib.utils.colors import conv_s2i


class IRCCommands(object):
    def rawcmd(self, cmd):
        self.out_msg.put(':%s %s' % (self.cnick, cmd))

    def password(self, password=None):
        if password:
            self.rawcmd('PASS %s' % password)

    def nick(self, nick=None):
        if not nick:
            nick = self.cnick
        self.rawcmd('NICK %s' % nick)

    def user(self, user=None, host=None, server=None, real=None):
        if not user:
            user = self.cnick
        if not host:
            host = self.cnick
        if not server:
            server = self.cnick
        if not real:
            real = ':%s' % self.cnick.upper()
        self.rawcmd('USER %s %s %s %s' % (user, host, server, real))

    def pong(self, timestamp):
        self.rawcmd('PONG %s' % timestamp)

    def join(self, chan, key=None):
        self.locks['ServReg'].acquire()
        while not self.bot.irc_status['Registered']:
            self.locks['ServReg'].wait()
        self.locks['ServReg'].release()

        if key:
            self.rawcmd('JOIN %s %s' % (chan, key))
        else:
            self.rawcmd('JOIN %s' % chan)

    def privmsg(self, target, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        self.rawcmd('PRIVMSG %s :%s' % (target, msg))

    def notice(self, target, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        self.rawcmd('NOTICE %s :%s' % (target, msg))

    def names(self, channels=''):
        self.rawcmd('NAMES %s' % channels)

    def kick(self, chan, nick, comment='because...'):
        self.rawcmd('KICK %s %s :%s' % (chan, nick, comment))

    def whois(self, nick):
        self.rawcmd('WHOIS %s' % nick)
