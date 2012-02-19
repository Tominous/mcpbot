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

            # parse the various fields out of the message
            prefix = ''
            trailing = []
            if msg[0] == ':':
                prefix, msg = msg[1:].split(' ', 1)
            if msg.find(' :') != -1:
                msg, trailing = msg.split(' :', 1)
                args = msg.split()
                args.append(trailing)
            else:
                args = msg.split()
            # uppercase the command as mIRC is lame apparently, shouldn't matter as we are talking to a server anyway
            command = args.pop(0).upper()

            # If the reply is numerical, we change the cmd type to the correct type
            if command in IRC_REPLIES:
                command = IRC_REPLIES[command]

            # fake event used for logging and onDefault, missing target
            ev = Event(prefix, command, '', str(args), 'IRC')
            self.bot.loggingq.put(ev)

            # We call the corresponding raw event if it exist, or the rawDefault if not.
            if hasattr(self, 'onIRC_%s' % command):
                self.bot.threadpool.add_task(getattr(self, 'onIRC_%s' % command), prefix, args)
            else:
                self.bot.threadpool.add_task(getattr(self, 'onIRC_Default'), command, prefix, args)

            # We call the corresponding event if it exist, or the Default if not.
            if hasattr(self.bot, 'onIRC_%s' % command):
                self.bot.threadpool.add_task(getattr(self.bot, 'onIRC_%s' % command), prefix, args)
            elif hasattr(self.bot, 'onIRC_Default'):
                self.bot.threadpool.add_task(getattr(self.bot, 'onIRC_Default'), command, prefix, args)
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
            self.log('WARNING : Tried to remove an inexisting user : %s.' % nick)
            return

        if not chan:
            del self.bot.users[nick]
            return

        if chan in self.bot.users[nick].chans:
            del self.bot.users[nick].chans[chan]
        if not len(self.bot.users[nick].chans):
            del self.bot.users[nick]
