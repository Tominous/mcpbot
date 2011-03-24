class User(object):
    def __init__(self, nick):
        self.nick   = nick
        self.status = -1
        self.host   = -1
        self.ip     = -1
        self.chans  = {}
        self.socket = None

    def get_string(self):
        return '< User %s, Status: %s, Host: %s, IP: %s, Chans: %s >'%(self.nick, self.status, self.host, self.ip, self.chans)
        
