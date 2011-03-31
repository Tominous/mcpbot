import time

class Event(object):
    
    maxid = 0
    
    def __init__(self, sender, cmd, target, msg, selfnick, etype):
        if   msg[0]    == ':' and len(msg.strip()) == 1: msg=''
        elif msg[0]    == ':': msg=msg[1:] 
        if sender and sender[0] == ':': sender=sender[1:]
        if target and target[0] == ':': target=target[1:]
        self.sender     = sender.split('!')[0].strip()
        self.senderfull = sender.strip()
        self.cmd        = cmd.strip()
        self.target     = target.strip()
        if target:self.ischan = target[0] in ['#','&']
        else: self.ischan    = False
        self.msg        = msg.strip()
        self.type       = etype
        self.stamp      = time.time()
        self.chan       = None
        self.id         = Event.maxid
        Event.maxid    += 1
        if self.ischan: self.chan = self.target


    
