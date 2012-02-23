from irc_lib.utils.irc_name import get_nick, get_ip
from irc_lib.protocols.event import Event


class IRCRawEvents(object):
    def onIRC_PING(self, prefix, args):
        target = args[0]
        if len(args) > 1:
            target2 = args[1]
        else:
            target2 = None
        self.pong(target, target2)


    def onIRC_PRIVMSG(self, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        msg = args[1]

        ischan = target[0] in ['#', '&']

        if not len(msg):
            return

        outcmd = None

        if ischan and msg[0] == self.bot.controlchar:
            outcmd = msg.split()[0][1:]

        if target == self.cnick and msg[0] != self.bot.controlchar:
            outcmd = msg.split()[0]

        if outcmd:
            if len(msg.split()) < 2:
                outmsg = ' '
            else:
                outmsg = ' '.join(msg.split()[1:])
            evcmd = Event(sender, outcmd, target, outmsg, 'CMD')
            self.bot.commandq.put(evcmd)

    def onIRC_JOIN(self, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        if len(args) > 1:
            key = args[1]
        else:
            key = None
        if sender == self.cnick:
            self.bot.irc_status['Channels'].add(chan)
        else:
            self.add_user(sender, chan)

    def onIRC_PART(self, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        if len(args) > 1:
            msg = args[1]
        else:
            msg = ''
        self.rm_user(sender, chan)

    def onIRC_QUIT(self, prefix, args):
        sender = get_nick(prefix)
        if len(args) > 0:
            msg = args[0]
        else:
            msg = ''
        self.rm_user(sender)

    def onIRC_RPL_WELCOME(self, prefix, args):
        server = prefix
        target = args[0]
        if len(args) > 1:
            msg = args[1]
        else:
            msg = ''
        self.bot.irc_status['Server'] = server
        self.log('> Connected to server %s' % server)

    def onIRC_RPL_MOTDSTART(self, prefix, args):
        server = prefix
        target = args[0]
        msg = args[1]
        if server == self.bot.irc_status['Server']:
            self.locks['ServReg'].acquire()
            self.bot.irc_status['Registered'] = True
            self.locks['ServReg'].notifyAll()
            self.locks['ServReg'].release()
            self.log('> MOTD found. Registered with server.')

    def onIRC_RPL_NAMREPLY(self, prefix, args):
        server = prefix
        # Used for channel status, "@" is used for secret channels, "*" for private channels, and "=" for others (public channels).
        target = args[0]
        channeltype = args[1]
        channel = args[2]
        nicks = args[3].split()

        for nick in nicks:
            self.add_user(nick, channel)

    def onIRC_RPL_WHOISUSER(self, prefix, args):
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

    def onIRC_NICK(self, prefix, args):
        sender = get_nick(prefix)
        newnick = args[0]
        if sender == self.cnick:
            return
        if sender in self.bot.users:
            self.bot.users[newnick] = self.bot.users[sender]
            del self.bot.users[sender]

    def onIRC_INVITE(self, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        chan = args[1]
        self.join(chan)

    def onIRC_Default(self, command, prefix, args):
        pass
