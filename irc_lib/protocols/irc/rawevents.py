from irc_lib.utils.irc_name import get_nick, get_ip, split_prefix
from irc_lib.protocols.event import Event


class IRCRawEvents(object):
    def onRawPING(self, prefix, args):
        target = args[0]
        self.pong(target)

#

    def onRawPRIVMSG(self, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        msg = args[1]

        ischan = target[0] in ['#', '&']

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

    def onRawJOIN(self, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        if sender == self.cnick:
            self.bot.irc_status['Channels'].add(chan)
        else:
            self.add_user(sender, chan)

    def onRawPART(self, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        msg = args[1]
        self.rm_user(sender, chan)

    def onRawQUIT(self, prefix, args):
        sender = get_nick(prefix)
        msg = args[0]
        self.rm_user(sender)

    def onRawRPL_WELCOME(self, prefix, args):
        server = prefix
        target = args[0]
        msg = args[1]
        self.bot.irc_status['Server'] = prefix
        self.log('> Connected to server %s' % prefix)

    def onRawRPL_MOTDSTART(self, prefix, args):
        server = prefix
        target = args[0]
        msg = args[1]
        if prefix == self.bot.irc_status['Server']:
            self.locks['ServReg'].acquire()
            self.bot.irc_status['Registered'] = True
            self.locks['ServReg'].notifyAll()
            self.locks['ServReg'].release()
            self.log('> MOTD found. Registered with server.')

    def onRawRPL_NAMREPLY(self, prefix, args):
        server = prefix
        # Used for channel status, "@" is used for secret channels, "*" for private channels, and "=" for others (public channels).
        target = args[0]
        channeltype = args[1]
        channel = args[2]
        nicks = args[3].split()

        for nick in nicks:
            self.add_user(nick, channel)

    def onRawRPL_WHOISUSER(self, prefix, args):
        sender = prefix
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

    def onRawNICK(self, prefix, args):
        sender = get_nick(prefix)
        newnick = args[0]
        if sender == self.cnick:
            return
        if sender in self.bot.users:
            self.bot.users[newnick] = self.bot.users[sender]
            del self.bot.users[sender]

    def onRawINVITE(self, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        chan = args[1]
        self.join(chan)

    def onRawDefault(self, command, prefix, args):
        self.bot.printq.put("Raw%s %s %s" % (command, repr(split_prefix(prefix)), str(args)))
