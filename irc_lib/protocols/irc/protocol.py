from Queue import Empty

from irc_lib.protocols.event import Event
from irc_lib.protocols.user import User
from commands import IRCCommands
from rawevents import IRCRawEvents
from constants import IRC_REPLIES


class IRCProtocol(IRCCommands, IRCRawEvents):
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick = _nick
        self.out_msg = _out_msg
        self.in_msg = _in_msg
        self.bot = _bot
        self.locks = _locks

        self.bot.threadpool.add_task(self.treat_msg, _threadname='IRCHandler')

    def log(self, msg):
        self.bot.log(msg)

    def treat_msg(self):
        while not self.bot.exit:
            # We check for msgs on the queue
            try:
                msg = self.in_msg.get(True, 1)
            except Empty:
                continue
            self.in_msg.task_done()

            # We check if we have an actual msg or if it is empty (never should be)
            msg = msg.strip()
            if not msg:
                continue

            msg = msg.split()

            # If the reply is numerical, we change the cmd type to the correct type
            if msg[1] in IRC_REPLIES:
                msg[1] = IRC_REPLIES[msg[1]]

            # We treat the ping special case
            if msg[0] == 'PING':
                self.onRawPING(msg)
                if hasattr(self.bot, 'onPING'):
                    self.bot.onPING(msg)
                continue

            # We add an space to the msg if the msg is less than 3 elements (we create an actual msg field for the event object)
            if len(msg) < 4:
                msg.append(' ')

            # We treat the special case of QUIT.
            # If we don't have a QUIT, we create a normal event
            if msg[1] == 'QUIT':
                ev = Event(msg[0], msg[1], '', ' '.join(msg[2:]), 'IRC')
            else:
                ev = Event(msg[0], msg[1], msg[2], ' '.join(msg[3:]), 'IRC')

            self.log(ev)

            # We call the corresponding raw event if it exist, or the rawDefault if not.
            if hasattr(self, 'onRaw%s' % ev.cmd):
                self.bot.threadpool.add_task(getattr(self, 'onRaw%s' % ev.cmd), ev)
            else:
                self.bot.threadpool.add_task(getattr(self, 'onRawDefault'), ev)

            # We call the corresponding event if it exist, or the Default if not.
            if hasattr(self.bot, 'on%s' % ev.cmd):
                self.bot.threadpool.add_task(getattr(self.bot, 'on%s' % ev.cmd), ev)
            else:
                self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'), ev)

    def add_user(self, nick, chan=None):
        nick_status = '-'
        if nick[0] == ':':
            nick = nick[1:]
        snick = nick
        if nick[0] in ['@', '+']:
            snick = nick[1:]
            nick_status = nick[0]

        if not snick in self.bot.users:
            self.bot.users[snick] = User(snick)
        if not chan:
            return
        self.bot.users[snick].chans[chan] = nick_status

    def rm_user(self, nick, chan=None):
        if nick[0] == ':':
            nick = nick[1:]

        if not nick in self.bot.users:
            print 'WARNING : Tried to remove an inexisting user : %s.' % nick
            return

        if not chan:
            del self.bot.users[nick]
            return

        if chan in self.bot.users[nick].chans:
            del self.bot.users[nick].chans[chan]
        if not len(self.bot.users[nick].chans):
            del self.bot.users[nick]
