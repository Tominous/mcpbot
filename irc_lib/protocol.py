import logging


class Protocol(object):
    def __init__(self, nick, locks, bot, parent, logger='IRCBot.protocol'):
        self.logger = logging.getLogger(logger)
        self.cnick = nick
        self.locks = locks
        self.bot = bot
        self.parent = parent
