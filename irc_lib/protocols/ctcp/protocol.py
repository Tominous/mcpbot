from irc_lib.protocols.dcc.protocol import DCCProtocol
from irc_lib.protocols.event import Event
from commands import CTCPCommands
from rawevents import CTCPRawEvents
from constants import CTCP_DELIMITER


class CTCPProtocol(CTCPCommands, CTCPRawEvents):
    def __init__(self, _nick, _locks, _bot, _parent):
        self.cnick = _nick
        self.locks = _locks
        self.bot = _bot
        self.irc = _parent

        self.dcc = DCCProtocol(self.cnick, self.locks, self.bot, self)

    def log(self, msg):
        self.bot.log(msg)

    def eventlog(self, ev):
        self.bot.eventlog(ev)

    def process_msg(self, prefix, target, msg):
        # remove leading/trailing CTCP_DELIMITER
        if msg[-1] == CTCP_DELIMITER:
            msg = msg[1:-1]
        else:
            msg = msg[1:]

        cmd, _, data = msg.partition(' ')

        ev = Event(prefix, cmd, target, data, 'CTCP')
        self.eventlog(ev)

        cmd_func = getattr(self, 'onCTCP_%s' % ev.cmd, self.onCTCP_Default)
        cmd_func(ev)

        cmd_func = getattr(self.bot, 'onCTCP_%s' % ev.cmd, getattr(self.bot, 'onCTCP_Default', self.bot.onDefault))
        cmd_func(ev)
