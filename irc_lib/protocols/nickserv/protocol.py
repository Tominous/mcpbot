import logging

from irc_lib.protocols.event import Event
from commands import NickServCommands
from rawevents import NickServRawEvents


class NickServProtocol(NickServCommands, NickServRawEvents):
    def __init__(self, _nick, _locks, _bot, _parent):
        self.logger = logging.getLogger('IRCBot.NSRV')
        self.cnick = _nick
        self.locks = _locks
        self.bot = _bot
        self.irc = _parent

    def eventlog(self, ev):
        self.bot.eventlog(ev)

    def process_msg(self, prefix, target, msg):
        split_msg = msg.split()
        if len(split_msg) > 1 and split_msg[1] in ['ACC']:
            cmd = split_msg[1]
        else:
            cmd = 'Unknown'

        ev = Event(prefix, cmd, target, msg, 'NSRV')
        self.eventlog(ev)

        cmd_func = getattr(self, 'onNSRV_%s' % ev.cmd, self.onNSRV_Default)
        cmd_func(ev)

        cmd_func = getattr(self.bot, 'onNSRV_%s' % ev.cmd, getattr(self.bot, 'onNSRV_Default', self.bot.onDefault))
        cmd_func(ev)
