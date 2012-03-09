from irc_lib.utils.colors import conv_s2i


class IRCCommands(object):
    def rawcmd(self, cmd, args=None, text=None):
        if args is None:
            args = []
        if not isinstance(args, list):
            raise TypeError
        nick = ':' + self.cnick
        out_list = [nick, cmd]
        out_list.extend(args)
        if text:
            text = ':' + text
            out_list.append(text)
        out = ' '.join(out_list)
        self.bot.rawcmd(out)

    def password(self, password=None):
        if password:
            self.rawcmd('PASS', [password])

    def nick(self, nick=None):
        if not nick:
            nick = self.cnick
        self.rawcmd('NICK', [nick])

    def user(self, user=None, host=None, server=None, real=None):
        if not user:
            user = self.cnick
        if not host:
            host = self.cnick
        if not server:
            server = self.cnick
        if not real:
            real = self.cnick.upper()
        self.rawcmd('USER', [user, host, server], real)

    def pong(self, server1, server2=None):
        if server2:
            self.rawcmd('PONG', [server1, server2])
        else:
            self.rawcmd('PONG', [server1])

    def join(self, chan, key=None):
        self.locks['ServReg'].acquire()
        while not self.bot.irc_status['Registered']:
            self.locks['ServReg'].wait()
        self.locks['ServReg'].release()

        if key:
            self.rawcmd('JOIN', [chan, key])
        else:
            self.rawcmd('JOIN', [chan])

    def privmsg(self, target, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        self.rawcmd('PRIVMSG', [target], msg)

    def notice(self, target, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        self.rawcmd('NOTICE', [target], msg)

    def names(self, channels=''):
        self.rawcmd('NAMES', [channels])

    def kick(self, chan, nick, comment='because...'):
        self.rawcmd('KICK', [chan, nick], comment)

    def whois(self, nick):
        self.rawcmd('WHOIS', [nick])
