import time

from irc_lib.utils.irc_name import split_prefix


class Event(object):
    maxid = 0

    def __init__(self, sender, cmd, target, msg, etype):
        if msg and msg[0] == ':':
            print '*** Event: : in msg: %s' % repr(msg)
            msg = msg[1:]
        if sender and sender[0] == ':':
            print '*** Event: : in sender: %s' % repr(sender)
            sender = sender[1:]
        if target and target[0] == ':':
            print '*** Event: : in target: %s' % repr(target)
            target = target[1:]
        if sender != sender.strip():
            print '*** Event: sender stripped: %s' % repr(target)
        if cmd != cmd.strip():
            print '*** Event: cmd stripped: %s' % repr(cmd)
        if target != target.strip():
            print '*** Event: target stripped: %s' % repr(target)
        self.sender, self.senderuser, self.senderhost = split_prefix(sender.strip())
        self.senderfull = sender.strip()
        self.cmd = cmd.strip()
        self.target = target.strip()
        if target:
            self.ischan = target[0] in ['#', '&']
        else:
            self.ischan = False
        self.msg = msg.strip()
        self.type = etype
        self.stamp = time.time()
        self.chan = None
        self.id = Event.maxid
        Event.maxid += 1
        if self.ischan:
            self.chan = self.target

    def __repr__(self):
        return '< Event : [%s][%s][%s] S: %s T: %s M: %s >' % (time.ctime(), self.type.ljust(5), self.cmd.ljust(10), self.sender.ljust(20), self.target.ljust(20), self.msg)
