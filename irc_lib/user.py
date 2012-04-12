class User(object):
    def __init__(self, nick):
        self.nick = nick
        self.status = None
        self.host = None
        self.ip = None
        self.chans = {}
        self.socket = None

    def get_string(self):
        return '< User %s, Status: %s, Host: %s, IP: %s, Chans: %s >' % (self.nick, self.status, self.host, self.ip,
                                                                         self.chans)
