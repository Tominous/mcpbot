import time

from irc_lib.utils.irc_name import get_ip
from irc_lib.protocols.event import Event


class IRCRawEvents(object):
    def onRawPING(self, msg):
        self.pong(msg[1])

#

    def onRawPRIVMSG(self, ev):
        if not ev.msg:
            return

        outcmd = None

        if ev.ischan and ev.msg[0] == self.bot.controlchar:
            outcmd = ev.msg.split()[0][1:]

        if ev.target == self.cnick and ev.msg[0] != self.bot.controlchar:
            outcmd = ev.msg.split()[0]

        if outcmd:
            if len(ev.msg.split()) < 2:
                outmsg = ' '
            else:
                outmsg = ' '.join(ev.msg.split()[1:])
            evcmd = Event(ev.sender, outcmd, ev.target, outmsg, self.cnick, 'CMD')
            self.bot.commandq.put(evcmd)

    def onRawJOIN(self, ev):
        if ev.sender == self.cnick:
            self.bot.irc_status['Channels'].add(ev.chan)
        else:
            c = self.bot.acquiredb()
            self.add_user(ev.sender, ev.chan, ev.senderuser, ev.senderhost, c)
            self.bot.releasedb(c)

    def onRawPART(self, ev):
        self.rm_user(ev.sender, ev.chan)

    def onRawQUIT(self, ev):
        self.rm_user(ev.sender)

        c = self.bot.acquiredb()
        c.execute("""UPDATE nicks SET timestamp = ?, online = ? WHERE nick = ?""", (int(time.time()), 0, ev.sender))
        self.bot.releasedb(c)

    def onRawRPL_WELCOME(self, ev):
        self.bot.irc_status['Server'] = ev.sender
        self.bot.printq.put('> Connected to server %s' % ev.sender)

    def onRawRPL_MOTDSTART(self, ev):
        if ev.sender == self.bot.irc_status['Server']:
            self.locks['ServReg'].acquire()
            self.bot.irc_status['Registered'] = True
            self.locks['ServReg'].notifyAll()
            self.locks['ServReg'].release()
            self.bot.printq.put('> MOTD found. Registered with server.')

    def onRawRPL_NAMREPLY(self, ev):
        if not ev.msg:
            return
        # Used for channel status, "@" is used for secret channels, "*" for private channels, and "=" for others (public channels).
        weirdsymbol = ev.msg.split()[0]
        channel = ev.msg.split()[1]
        nicks = ev.msg.split()[2:]

        c = self.bot.acquiredb()
        for nick in nicks:
            self.add_user(nick, channel, c=c)
        self.bot.releasedb(c)

    def onRawRPL_WHOISUSER(self, ev):
        if not ev.msg:
            return
        nick = ev.msg.split()[0]
        user = ev.msg.split()[1]
        host = ev.msg.split()[2]
        real = ' '.join(ev.msg.split()[4:])[1:]

        self.locks['WhoIs'].acquire()
        if nick in self.bot.users:
            self.bot.users[nick].host = host
            self.bot.users[nick].ip = get_ip(host)
        self.locks['WhoIs'].notifyAll()
        self.locks['WhoIs'].release()

        c = self.bot.acquiredb()
        c.execute("""UPDATE nicks SET user=?, host=? WHERE nick = ?""", (user, host, nick))
        self.bot.releasedb(c)


    def onRawNICK(self, ev):
        if ev.sender == self.cnick:
            return
        if ev.sender in self.bot.users:
            self.bot.users[ev.target] = self.bot.users[ev.sender]
            del self.bot.users[ev.sender]

    def onRawINVITE(self, ev):
        if not ev.msg:
            return
        self.join(ev.msg)

    def onRawDefault(self, ev):
        pass
