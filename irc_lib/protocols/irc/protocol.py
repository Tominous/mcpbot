import logging

from irc_lib.protocols.nickserv.protocol import NickServProtocol
from irc_lib.protocols.ctcp import CTCPProtocol
from irc_lib.event import Event
from irc_lib.user import User
from irc_lib.protocols.irc.commands import IRCCommands
from irc_lib.protocols.irc.rawevents import IRCRawEvents
from irc_lib.protocols.irc.constants import IRC_REPLIES


class IRCProtocol(IRCCommands, IRCRawEvents):
    def __init__(self, _nick, _locks, _bot, _parent):
        self.logger = logging.getLogger('IRCBot.IRC')
        self.cnick = _nick
        self.locks = _locks
        self.bot = _bot

        self.nickserv = NickServProtocol(self.cnick, self.locks, self.bot, self)
        self.ctcp = CTCPProtocol(self.cnick, self.locks, self.bot, self)
        self.dcc = self.ctcp.dcc

    def eventlog(self, ev):
        self.bot.eventlog(ev)

    def process_msg(self, msg):
        # parse the various fields out of the message
        if msg[0] == ':':
            prefix, _, msg = msg[1:].partition(' ')
        else:
            prefix = ''
        msg, _, trailing = msg.partition(' :')
        args = msg.split()
        if trailing:
            args.append(trailing)

        # uppercase the command as mIRC is lame apparently, shouldn't matter as we are talking to a server anyway
        cmd = args.pop(0).upper()

        # If the reply is numerical, we change the cmd type to the correct type
        if cmd in IRC_REPLIES:
            cmd = IRC_REPLIES[cmd]

        # fake event used for logging and onDefault, missing target
        ev = Event(prefix, cmd, '', str(args), 'IRC')
        self.eventlog(ev)

        # We call the corresponding raw event if it exist, or the rawDefault if not.
        cmd_func = getattr(self, 'onIRC_%s' % cmd, self.onIRC_Default)
        self.bot.threadpool.add_task(cmd_func, cmd, prefix, args)

        # We call the corresponding event if it exist, or the Default if not.
        cmd_func = getattr(self.bot, 'onIRC_%s' % cmd, getattr(self.bot, 'onIRC_Default', None))
        if cmd_func:
            self.bot.threadpool.add_task(cmd_func, cmd, prefix, args)
        else:
            self.bot.threadpool.add_task(self.bot.onDefault, ev)

    def add_user(self, nick, chan=None):
        nick_status = '-'
        if nick[0] == ':':
            self.logger.warn('*** IRC.add_user: : in nick: %s', nick)
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
            self.logger.warn('*** IRC.rm_user: : in nick: %s', nick)
            nick = nick[1:]

        if not nick in self.bot.users:
            self.logger.error('*** IRC.rm_user: unknown: %s', nick)
            return

        if not chan:
            del self.bot.users[nick]
            return

        if chan in self.bot.users[nick].chans:
            del self.bot.users[nick].chans[chan]
        if not len(self.bot.users[nick].chans):
            del self.bot.users[nick]
