from Queue import Empty

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

        self.bot.threadpool.add_task(self.treat_msg, _threadname='NickServHandler')

    def log(self, msg):
        self.bot.log(msg)

    def treat_msg(self):
        while not self.bot.exit:
            try:
                msg = self.in_msg.get(True, 1)
            except Empty:
                continue
            self.in_msg.task_done()

            msg = msg.strip()
            if not msg:
                continue

            msg = msg.split()

            if len(msg) < 5:
                msg.append(' ')
            ev = Event(msg[0], msg[4], msg[2], ' '.join([msg[3], msg[5]]), 'NSERV')

            if hasattr(self, 'onNSERV_%s' % ev.cmd):
                self.bot.threadpool.add_task(getattr(self, 'onNSERV_%s' % ev.cmd), ev)
            else:
                self.bot.threadpool.add_task(getattr(self, 'onNSERV_Default'), ev)

            if hasattr(self.bot, 'onNSERV_%s' % ev.cmd):
                self.bot.threadpool.add_task(getattr(self.bot, 'onNSERV_%s' % ev.cmd), ev)
            elif hasattr(self.bot, 'onNSERV_Default'):
                self.bot.threadpool.add_task(getattr(self.bot, 'onNSERV_Default'), ev)
            else:
                self.bot.threadpool.add_task(getattr(self.bot, 'onDefault'), ev)
