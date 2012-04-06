from irc_lib.event import Event
from irc_lib.user import User
from irc_lib.utils.colors import conv_s2i
from irc_lib.utils.ircname import get_nick, get_ip
from irc_lib.protocol import Protocol
from irc_lib.protocols.ctcp import CTCPProtocol, CTCP_DELIMITER
from irc_lib.protocols.nickserv import NickServProtocol, NICKSERV


class IRCProtocol(Protocol):
    def __init__(self, _nick, _locks, _bot, _parent):
        Protocol.__init__(self, _nick, _locks, _bot, _parent, 'IRCBot.IRC')
        self.nickserv = NickServProtocol(self.cnick, self.locks, self.bot, self)
        self.ctcp = CTCPProtocol(self.cnick, self.locks, self.bot, self)
        self.dcc = self.ctcp.dcc

    def process_msg(self, msg):
        if not msg:
            return

        # parse the various fields out of the message
        if msg[0] == ':':
            prefix, _, msg = msg[1:].partition(' ')
        else:
            prefix = ''
        msg, _, trailing = msg.partition(' :')
        args = msg.split()
        if trailing:
            args.append(trailing)

        # uppercase the command as mIRC is lame apparently, shouldn't matter as we are talking to a server anyway
        cmd = args.pop(0).upper()

        # If the reply is numerical, we change the cmd type to the correct type
        if cmd in _IRC_REPLIES:
            cmd = _IRC_REPLIES[cmd]

        # We call the corresponding raw event if it exist, or the rawDefault if not.
        cmd_func = getattr(self, 'onIRC_%s' % cmd, self.onIRC_Default)
        self.bot.threadpool.add_task(cmd_func, cmd, prefix, args)

        # We call the corresponding event if it exist, or the Default if not.
        cmd_func = getattr(self.bot, 'onIRC_%s' % cmd, getattr(self.bot, 'onIRC_Default', None))
        if cmd_func:
            self.bot.threadpool.add_task(cmd_func, cmd, prefix, args)
        else:
            # fake event used for logging and onDefault, missing target
            ev = Event(prefix, cmd, '', str(args), 'IRC')
            self.bot.threadpool.add_task(self.bot.onDefault, ev)

    def add_user(self, nick, chan=None):
        nick_status = '-'
        snick = nick
        if nick[0] in ['@', '+']:
            snick = nick[1:]
            nick_status = nick[0]

        if snick not in self.bot.users:
            self.bot.users[snick] = User(snick)
        if not chan:
            return
        self.bot.users[snick].chans[chan] = nick_status

    def rm_user(self, nick, chan=None):
        if nick not in self.bot.users:
            self.logger.info('*** IRC.rm_user: unknown: %s', nick)
            return

        if not chan:
            del self.bot.users[nick]
            return

        if chan in self.bot.users[nick].chans:
            del self.bot.users[nick].chans[chan]
        if not len(self.bot.users[nick].chans):
            del self.bot.users[nick]

    def onIRC_PING(self, cmd, prefix, args):
        target = args[0]
        if len(args) > 1:
            target2 = args[1]
        else:
            target2 = None
        self.pong(target, target2)

    def onIRC_NOTICE(self, cmd, prefix, args):
        self.onIRC_PRIVMSG(cmd, prefix, args)

    def onIRC_PRIVMSG(self, cmd, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        msg = args[1]

        if not msg:
            return

        if sender == NICKSERV:
            self.nickserv.process_msg(prefix, target, msg)
            return

        if msg[0] == CTCP_DELIMITER:
            self.ctcp.process_msg(prefix, target, msg)
            return

        if cmd == 'PRIVMSG':
            self.bot.process_msg(sender, target, msg)

    def onIRC_JOIN(self, cmd, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        if len(args) > 1:
            key = args[1]
        else:
            key = None
        if sender == self.cnick:
            self.bot.channels.add(chan)
            self.logger.info('# Joined %s', chan)
        else:
            self.add_user(sender, chan)

    def onIRC_PART(self, cmd, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        if len(args) > 1:
            msg = args[1]
        else:
            msg = ''
        self.rm_user(sender, chan)

    def onIRC_QUIT(self, cmd, prefix, args):
        sender = get_nick(prefix)
        if len(args) > 0:
            msg = args[0]
        else:
            msg = ''
        self.rm_user(sender)

    def onIRC_RPL_WELCOME(self, cmd, prefix, args):
        server = prefix
        target = args[0]
        if len(args) > 1:
            msg = args[1]
        else:
            msg = ''
        self.locks['ServReg'].set()
        self.logger.info('# Connected to %s', server)

    def onIRC_RPL_NAMREPLY(self, cmd, prefix, args):
        server = prefix
        # Used for channel status, "@" is used for secret channels, "*" for private channels, and "=" for others (public channels).
        target = args[0]
        channeltype = args[1]
        channel = args[2]
        nicks = args[3].split()

        for nick in nicks:
            self.add_user(nick, channel)

    def onIRC_RPL_WHOISUSER(self, cmd, prefix, args):
        server = prefix
        target = args[0]
        nick = args[1]
        user = args[2]
        host = args[3]
        real = args[4]

        with self.locks['WhoIs']:
            if nick not in self.bot.users:
                self.bot.users[nick] = User(nick)
            self.bot.users[nick].host = host
            self.bot.users[nick].ip = get_ip(host)
            self.locks['WhoIs'].notifyAll()

    def onIRC_NICK(self, cmd, prefix, args):
        sender = get_nick(prefix)
        newnick = args[0]
        if sender == self.cnick:
            return
        if sender in self.bot.users:
            self.bot.users[newnick] = self.bot.users[sender]
            del self.bot.users[sender]

    def onIRC_INVITE(self, cmd, prefix, args):
        sender = get_nick(prefix)
        target = args[0]
        chan = args[1]
        self.logger.info('# Invited to %s by %s', chan, sender)
        self.join(chan)

    def onIRC_KICK(self, cmd, prefix, args):
        sender = get_nick(prefix)
        chan = args[0]
        target = args[1]
        reason = args[2]
        if target == self.cnick:
            self.logger.info('# Kicked from %s by %s %s', chan, sender, repr(reason))
            self.bot.channels.discard(chan)
        else:
            self.rm_user(target, chan)

    def onIRC_ERR_NOSUCHNICK(self, cmd, prefix, args):
        server = prefix
        target = args[0]
        nick = args[1]
        reason = args[2]
        if nick == NICKSERV:
            self.nickserv.no_nickserv()
        else:
            self.rm_user(nick)

    def onIRC_ERR_NEEDREGGEDNICK(self, cmd, prefix, args):
        server = prefix
        nick = args[0]
        chan = args[1]
        reason = args[2]
        self.logger.warning('*** Join to %s failed: not identified', chan)

    def onIRC_ERR_INVITEONLYCHAN(self, cmd, prefix, args):
        server = prefix
        nick = args[0]
        chan = args[1]
        reason = args[2]
        self.logger.warning('*** Join to %s failed: invite only', chan)

    def onIRC_ERR_BANNEDFROMCHAN(self, cmd, prefix, args):
        server = prefix
        nick = args[0]
        chan = args[1]
        reason = args[2]
        self.logger.warning('*** Join to %s failed: banned', chan)

    def onIRC_Default(self, cmd, prefix, args):
        pass

    def rawcmd(self, cmd, args=None, text=None):
        if args is None:
            args = []
        if not isinstance(args, list):
            raise TypeError
        nick = ':' + self.cnick
        out_list = [nick, cmd]
        out_list.extend(args)
        if text:
            text = ':' + text
            out_list.append(text)
        out = ' '.join(out_list)
        self.bot.rawcmd(out)

    def password(self, password=None):
        if password:
            self.rawcmd('PASS', [password])

    def nick(self, nick=None):
        if not nick:
            nick = self.cnick
        self.rawcmd('NICK', [nick])

    def user(self, user=None, host=None, server=None, real=None):
        if not user:
            user = self.cnick
        if not host:
            host = self.cnick
        if not server:
            server = self.cnick
        if not real:
            real = self.cnick.upper()
        self.rawcmd('USER', [user, host, server], real)

    def pong(self, server1, server2=None):
        if server2:
            self.rawcmd('PONG', [server1, server2])
        else:
            self.rawcmd('PONG', [server1])

    def join(self, chan, key=None):
        if key:
            self.rawcmd('JOIN', [chan, key])
        else:
            self.rawcmd('JOIN', [chan])

    def privmsg(self, target, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        self.rawcmd('PRIVMSG', [target], msg)

    def notice(self, target, msg, color=True):
        if color:
            msg = conv_s2i(msg)
        self.rawcmd('NOTICE', [target], msg)

    def names(self, channels=''):
        self.rawcmd('NAMES', [channels])

    def kick(self, chan, nick, comment='because...'):
        self.rawcmd('KICK', [chan, nick], comment)

    def whois(self, nick):
        self.rawcmd('WHOIS', [nick])


_IRC_REPLIES = {
    '001': 'RPL_WELCOME',
    '002': 'RPL_YOURHOST',
    '003': 'RPL_CREATED',
    '004': 'RPL_MYINFO',
    '005': 'RPL_ISUPPORT',
    '200': 'RPL_TRACELINK',
    '201': 'RPL_TRACECONNECTING',
    '202': 'RPL_TRACEHANDSHAKE',
    '203': 'RPL_TRACEUNKNOWN',
    '204': 'RPL_TRACEOPERATOR',
    '205': 'RPL_TRACEUSER',
    '206': 'RPL_TRACESERVER',
    '208': 'RPL_TRACENEWTYPE',
    '211': 'RPL_STATSLINKINFO',
    '212': 'RPL_STATSCOMMANDS',
    '213': 'RPL_STATSCLINE',
    '214': 'RPL_STATSNLINE',
    '215': 'RPL_STATSILINE',
    '216': 'RPL_STATSKLINE',
    '218': 'RPL_STATSYLINE',
    '219': 'RPL_ENDOFSTATS',
    '221': 'RPL_UMODEIS',
    '241': 'RPL_STATSLLINE',
    '242': 'RPL_STATSUPTIME',
    '243': 'RPL_STATSOLINE',
    '244': 'RPL_STATSHLINE',
    '250': 'RPL_STATSCONN',
    '251': 'RPL_LUSERCLIENT',
    '252': 'RPL_LUSEROP',
    '253': 'RPL_LUSERUNKNOWN',
    '254': 'RPL_LUSERCHANNELS',
    '255': 'RPL_LUSERME',
    '256': 'RPL_ADMINME',
    '257': 'RPL_ADMINLOC1',
    '258': 'RPL_ADMINLOC2',
    '259': 'RPL_ADMINEMAIL',
    '261': 'RPL_TRACELOG',
    '265': 'RPL_LOCALUSERS',
    '266': 'RPL_GLOBALUSERS',
    '300': 'RPL_NONE',
    '301': 'RPL_AWAY',
    '302': 'RPL_USERHOST',
    '303': 'RPL_ISON',
    '305': 'RPL_UNAWAY',
    '306': 'RPL_NOWAWAY',
    '311': 'RPL_WHOISUSER',
    '312': 'RPL_WHOISSERVER',
    '313': 'RPL_WHOISOPERATOR',
    '314': 'RPL_WHOWASUSER',
    '315': 'RPL_ENDOFWHO',
    '317': 'RPL_WHOISIDLE',
    '318': 'RPL_ENDOFWHOIS',
    '319': 'RPL_WHOISCHANNELS',
    '321': 'RPL_LISTSTART',
    '322': 'RPL_LIST',
    '323': 'RPL_LISTEND',
    '324': 'RPL_CHANNELMODEIS',
    '330': 'RPL_WHOISSTATUS',
    '331': 'RPL_NOTOPIC',
    '332': 'RPL_TOPIC',
    '333': 'RPL_TOPICWHOTIME',
    '341': 'RPL_INVITING',
    '342': 'RPL_SUMMONING',
    '351': 'RPL_VERSION',
    '352': 'RPL_WHOREPLY',
    '353': 'RPL_NAMREPLY',
    '364': 'RPL_LINKS',
    '365': 'RPL_ENDOFLINKS',
    '366': 'RPL_ENDOFNAMES',
    '367': 'RPL_BANLIST',
    '368': 'RPL_ENDOFBANLIST',
    '369': 'RPL_ENDOFWHOWAS',
    '371': 'RPL_INFO',
    '372': 'RPL_MOTD',
    '374': 'RPL_ENDOFINFO',
    '375': 'RPL_MOTDSTART',
    '376': 'RPL_ENDOFMOTD',
    '381': 'RPL_YOUREOPER',
    '382': 'RPL_REHASHING',
    '391': 'RPL_TIME',
    '392': 'RPL_USERSSTART',
    '393': 'RPL_USERS',
    '394': 'RPL_ENDOFUSERS',
    '395': 'RPL_NOUSERS',
    '401': 'ERR_NOSUCHNICK',
    '402': 'ERR_NOSUCHSERVER',
    '403': 'ERR_NOSUCHCHANNEL',
    '404': 'ERR_CANNOTSENDTOCHAN',
    '405': 'ERR_TOOMANYCHANNELS',
    '406': 'ERR_WASNOSUCHNICK',
    '407': 'ERR_TOOMANYTARGETS',
    '409': 'ERR_NOORIGIN',
    '411': 'ERR_NORECIPIENT',
    '412': 'ERR_NOTEXTTOSEND',
    '413': 'ERR_NOTOPLEVEL',
    '414': 'ERR_WILDTOPLEVEL',
    '421': 'ERR_UNKNOWNCOMMAND',
    '422': 'ERR_NOMOTD',
    '423': 'ERR_NOADMININFO',
    '424': 'ERR_FILEERROR',
    '431': 'ERR_NONICKNAMEGIVEN',
    '432': 'ERR_ERRONEUSNICKNAME',
    '433': 'ERR_NICKNAMEINUSE',
    '436': 'ERR_NICKCOLLISION',
    '441': 'ERR_USERNOTINCHANNEL',
    '442': 'ERR_NOTONCHANNEL',
    '443': 'ERR_USERONCHANNEL',
    '444': 'ERR_NOLOGIN',
    '445': 'ERR_SUMMONDISABLED',
    '446': 'ERR_USERSDISABLED',
    '451': 'ERR_NOTREGISTERED',
    '461': 'ERR_NEEDMOREPARAMS',
    '462': 'ERR_ALREADYREGISTRED',
    '463': 'ERR_NOPERMFORHOST',
    '464': 'ERR_PASSWDMISMATCH',
    '465': 'ERR_YOUREBANNEDCREEP',
    '467': 'ERR_KEYSET',
    '471': 'ERR_CHANNELISFULL',
    '472': 'ERR_UNKNOWNMODE',
    '473': 'ERR_INVITEONLYCHAN',
    '474': 'ERR_BANNEDFROMCHAN',
    '475': 'ERR_BADCHANNELKEY',
    '477': 'ERR_NEEDREGGEDNICK',
    '481': 'ERR_NOPRIVILEGES',
    '482': 'ERR_CHANOPRIVSNEEDED',
    '483': 'ERR_CANTKILLSERVER',
    '491': 'ERR_NOOPERHOST',
    '501': 'ERR_UMODEUNKNOWNFLAG',
    '502': 'ERR_USERSDONTMATCH',
}
