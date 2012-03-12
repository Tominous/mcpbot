import time
import logging

from irc_lib.utils.irc_name import split_prefix


class Event(object):
    maxid = 0

    def __init__(self, sender, cmd, target, msg, etype):
        logger = logging.getLogger('IRCBot.Event')
        self.sender, self.senderuser, self.senderhost = split_prefix(sender)
        self.senderfull = sender
        self.cmd = cmd
        self.target = target
        self.msg = msg
        self.type = etype
        if target:
            self.ischan = target[0] in ['#', '&']
        else:
            self.ischan = False
        if self.ischan:
            self.chan = self.target
        else:
            self.chan = None
        self.stamp = time.time()
        self.id = Event.maxid
        Event.maxid += 1

    def __repr__(self):
        return '< Event : [%s][%s][%s] S: %s T: %s M: %s >' % (time.ctime(), self.type.ljust(5), self.cmd.ljust(10), self.sender.ljust(20), self.target.ljust(20), self.msg)
