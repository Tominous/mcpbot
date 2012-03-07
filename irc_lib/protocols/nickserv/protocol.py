from irc_lib.protocols.event import Event
from commands import NickServCommands
from rawevents import NickServRawEvents


class NickServProtocol(NickServCommands, NickServRawEvents):
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick = _nick
        self.out_msg = _out_msg
        self.in_msg = _in_msg
        self.bot = _bot
        self.locks = _locks

    def log(self, msg):
        self.bot.log(msg)

    def process_msg(self, prefix, target, msg):
        split_msg = msg.split()
        if len(split_msg) > 1 and split_msg[1] in ['ACC']:
            cmd = split_msg[1]
        else:
            cmd = 'Unknown'

        ev = Event(prefix, cmd, target, msg, 'NSERV')
        self.bot.loggingq.put(ev)

        cmd_func = getattr(self, 'onNSERV_%s' % ev.cmd, self.onNSERV_Default)
        self.bot.threadpool.add_task(cmd_func, ev)

        cmd_func = getattr(self.bot, 'onNSERV_%s' % ev.cmd, getattr(self.bot, 'onNSERV_Default', self.bot.onDefault))
        self.bot.threadpool.add_task(cmd_func, ev)
