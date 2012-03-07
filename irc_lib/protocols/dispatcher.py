from Queue import Queue, Empty

from irc_lib.protocols.irc.protocol import IRCProtocol
from irc_lib.protocols.nickserv.protocol import NickServProtocol
from irc_lib.protocols.ctcp.protocol import CTCPProtocol
from irc_lib.protocols.dcc.protocol import DCCProtocol


class Dispatcher(object):
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.in_msg = _in_msg

        self.bot = _bot

        self.irc_queue = Queue()

        self.irc = IRCProtocol(_nick, _out_msg, self.irc_queue, _locks, _bot)
        self.nse = NickServProtocol(_nick, _out_msg, None, _locks, _bot)
        self.ctcp = CTCPProtocol(_nick, _out_msg, None, _locks, _bot)
        self.dcc = DCCProtocol(_nick, _out_msg, None, _locks, _bot)

        _bot.threadpool.add_task(self.msg_loop, _threadname='Dispatcher')

    def msg_loop(self):
        while not self.bot.exit:
            try:
                msg = self.in_msg.get(True, 1)
            except Empty:
                continue
            self.in_msg.task_done()
            self.process_msg(msg)

    def process_msg(self, msg):
        self.irc_queue.put(msg)
