import socket
import logging


def get_nick(name):
    nick, _, _ = split_prefix(name)
    return nick


def get_host(name):
    _, _, host = split_prefix(name)
    return host


def get_ip(host):
    logger = logging.getLogger('IRCBot.irc_name')
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        logger.warning('*** irc_name.get_ip: socket.gaierror: %s', host)
        return '0.0.0.0'


def split_prefix(prefix):
    rest, _, host = prefix.partition('@')
    nick, _, user = rest.partition('!')
    return nick, user, host
