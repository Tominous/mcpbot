from Queue import Queue, Empty

from irc_lib.utils.irc_name import get_nick
from irc_lib.protocols.irc.protocol import IRCProtocol
from irc_lib.protocols.nickserv.protocol import NickServProtocol
from irc_lib.protocols.ctcp.protocol import CTCPProtocol
from irc_lib.protocols.ctcp.constants import CTCP_DELIMITER
from irc_lib.protocols.dcc.protocol import DCCProtocol


class Dispatcher(object):
    def __init__(self, _nick, _out_msg, _in_msg, _locks, _bot):
        self.in_msg = _in_msg

        self.bot = _bot

        self.irc_queue = Queue()
        self.nse_queue = Queue()
        self.dcc_queue = Queue()

        self.irc = IRCProtocol(_nick, _out_msg, self.irc_queue, _locks, _bot)
        self.nse = NickServProtocol(_nick, _out_msg, self.nse_queue, _locks, _bot)
        self.ctcp = CTCPProtocol(_nick, _out_msg, None, _locks, _bot)
        self.dcc = DCCProtocol(_nick, _out_msg, self.dcc_queue, _locks, _bot)

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
        msg = msg.strip()
        if not msg:
            return

        sender = get_nick(msg.split()[0])
        cmd = msg.split()[1]

        if sender.lower() == 'nickserv':
            self.nse_queue.put(msg)
        elif self.isCTCP(cmd, msg) and msg.split()[3][2:] == 'DCC':
            self.dcc_queue.put(msg)
        else:
            self.irc_queue.put(msg)

    def isCTCP(self, cmd, msg):
        if len(' '.join(msg.split()[3:])) < 2:
            return False
        if cmd in ['PRIVMSG', 'NOTICE'] and ' '.join(msg.split()[3:])[1] == CTCP_DELIMITER and ' '.join(msg.split()[3:])[-1] == CTCP_DELIMITER:
            return True
        else:
            return False
