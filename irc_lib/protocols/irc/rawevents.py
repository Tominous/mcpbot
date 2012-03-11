from irc_lib.utils.irc_name import get_nick, get_ip
from irc_lib.protocols.ctcp import CTCP_DELIMITER
from irc_lib.protocols.nickserv import NICKSERV


class IRCRawEvents(object):
    def onIRC_PING(self, cmd, prefix, args):
        target = args[0]
        if len(args) > 1:
            target2 = args[1]
        else:
            target2 = None
        self.pong(target, target2)

    def onIRC_NOTICE(self, cmd, prefix, args):
        self.onIRC_PRIVMSG(cmd, prefix, args)

    def onIRC_PRIVMSG(self, cmd, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        msg = args[1]

        if not msg:
            return

        if sender == NICKSERV:
            self.nickserv.process_msg(prefix, target, msg)
            return

        if msg[0] == CTCP_DELIMITER:
            self.ctcp.process_msg(prefix, target, msg)
            return

        if cmd == 'PRIVMSG':
            self.bot.process_msg(sender, target, msg)

    def onIRC_JOIN(self, cmd, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        if len(args) > 1:
            key = args[1]
        else:
            key = None
        if sender == self.cnick:
            self.bot.irc_status['Channels'].add(chan)
            self.logger.info('# Joined %s', chan)
        else:
            self.add_user(sender, chan)

    def onIRC_PART(self, cmd, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        if len(args) > 1:
            msg = args[1]
        else:
            msg = ''
        self.rm_user(sender, chan)

    def onIRC_QUIT(self, cmd, prefix, args):
        sender = get_nick(prefix)
        if len(args) > 0:
            msg = args[0]
        else:
            msg = ''
        self.rm_user(sender)

    def onIRC_RPL_WELCOME(self, cmd, prefix, args):
        server = prefix
        target = args[0]
        if len(args) > 1:
            msg = args[1]
        else:
            msg = ''
        self.bot.irc_status['Server'] = server
        self.logger.info('# Connected to %s', server)

    def onIRC_RPL_MOTDSTART(self, cmd, prefix, args):
        server = prefix
        target = args[0]
        msg = args[1]
        if server == self.bot.irc_status['Server']:
            self.locks['ServReg'].acquire()
            self.bot.irc_status['Registered'] = True
            self.locks['ServReg'].notifyAll()
            self.locks['ServReg'].release()
            self.logger.info('# MOTD found. Registered with server.')

    def onIRC_RPL_NAMREPLY(self, cmd, prefix, args):
        server = prefix
        # Used for channel status, "@" is used for secret channels, "*" for private channels, and "=" for others (public channels).
        target = args[0]
        channeltype = args[1]
        channel = args[2]
        nicks = args[3].split()

        for nick in nicks:
            self.add_user(nick, channel)

    def onIRC_RPL_WHOISUSER(self, cmd, prefix, args):
        server = prefix
        target = args[0]
        nick = args[1]
        user = args[2]
        host = args[3]
        real = args[4]

        self.locks['WhoIs'].acquire()
        if nick in self.bot.users:
            self.bot.users[nick].host = host
            self.bot.users[nick].ip = get_ip(host)
        self.locks['WhoIs'].notifyAll()
        self.locks['WhoIs'].release()

    def onIRC_NICK(self, cmd, prefix, args):
        sender = get_nick(prefix)
        newnick = args[0]
        if sender == self.cnick:
            return
        if sender in self.bot.users:
            self.bot.users[newnick] = self.bot.users[sender]
            del self.bot.users[sender]

    def onIRC_INVITE(self, cmd, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        chan = args[1]
        self.join(chan)

    def onIRC_Default(self, cmd, prefix, args):
        pass
