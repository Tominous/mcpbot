import logging


class Protocol(object):
    def __init__(self, _nick, _locks, _bot, _parent, _logger='IRCBot.protocol'):
        self.logger = logging.getLogger(_logger)
        self.cnick = _nick
        self.locks = _locks
        self.bot = _bot
        self.parent = _parent
