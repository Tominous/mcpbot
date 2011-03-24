import time

class Event(object):
    
    def __init__(self, sender, cmd, target, msg, selfnick, etype):
        if sender[0] == ':': sender=sender[1:]
        if target[0] == ':': target=target[1:]
        if msg[0]    == ':': msg=msg[1:]
        self.sender     = sender.split('!')[0].strip()
        self.senderfull = sender.strip()
        self.cmd        = cmd.strip()
        self.target     = target.strip()
        self.ischan     = target[0] in ['#','&']
        self.msg        = msg.strip()
        self.type       = etype
        self.stamp      = time.time()
        self.chan       = None
        if self.ischan: self.chan = self.target

    
