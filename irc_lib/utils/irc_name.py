import socket


def get_nick(name):
    if name[0] == ':': name = name[1:]
    return name.split('!')[0]


def get_host(name):
    return name.split('@')[-1]


def get_ip(host):
    try:
        return socket.gethostbyname(host)
    except socket.gaierror:
        return '0.0.0.0'
