from Queue import Empty

from irc_lib.protocols.event import Event
from commands import CTCPCommands
from rawevents import CTCPRawEvents


class CTCPProtocol(CTCPCommands, CTCPRawEvents):
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.cnick = _nick
        self.out_msg = _out_msg
        self.in_msg = _in_msg
        self.bot = _bot
        self.locks = _locks

        self.bot.threadpool.add_task(self.msg_loop, _threadname='CTCPHandler')

    def log(self, msg):
        self.bot.log(msg)

    def msg_loop(self):
        while not self.bot.exit:
            try:
                msg = self.in_msg.get(True, 1)
            except Empty:
                continue
            self.in_msg.task_done()
            self.process_msg(msg)

    def process_msg(self, msg):
        msg = msg.strip()
        if not msg:
            return

        msg = msg.split()
        msg[3] = ' '.join(msg[3:])
        msg = msg[:4]
        # We remove the leading/tailing \x01
        msg[3] = msg[3].replace('\x01', '')

        if len(msg[3].split()) < 2:
            outmsg = ' '
        else:
            outmsg = ' '.join(msg[3].split()[1:])

        ev = Event(msg[0], msg[3].split()[0][1:], msg[2], outmsg, 'CTCP')
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
