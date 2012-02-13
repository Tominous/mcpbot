class Error(Exception):
    pass


class IRCBotError(Error):
    def __init__(self, value):
        super(IRCBotError, self).__init__()
        self.value = value

    def __str__(self):
        return repr(self.value)
