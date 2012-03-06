from irc_lib.protocols.event import Event
from commands import CTCPCommands
from rawevents import CTCPRawEvents
from constants import CTCP_DELIMITER


class CTCPProtocol(CTCPCommands, CTCPRawEvents):
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick = _nick
        self.out_msg = _out_msg
        self.in_msg = _in_msg
        self.bot = _bot
        self.locks = _locks

    def log(self, msg):
        self.bot.log(msg)

    def process_msg(self, prefix, target, msg):
        # remove leading/trailing CTCP_DELIMITER
        if msg[-1] == CTCP_DELIMITER:
            msg = msg[1:-1]
        else:
            msg = msg[1:]

        cmd, _, data = msg.partition(' ')

        ev = Event(prefix, cmd, target, data, 'CTCP')
        self.bot.loggingq.put(ev)

        if hasattr(self, 'onCTCP_%s' % ev.cmd):
            self.bot.threadpool.add_task(getattr(self, 'onCTCP_%s' % ev.cmd), ev)
        else:
            self.bot.threadpool.add_task(getattr(self, 'onCTCP_Default'), ev)

        if hasattr(self.bot, 'onCTCP_%s' % ev.cmd):
            self.bot.threadpool.add_task(getattr(self.bot, 'onCTCP_%s' % ev.cmd), ev)
        elif hasattr(self.bot, 'onCTCP_Default'):
            self.bot.threadpool.add_task(getattr(self.bot, 'onCTCP_Default'), ev)
        else:
            self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'), ev)
