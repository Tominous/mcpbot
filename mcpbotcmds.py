import csv
import re
import threading

from irc_lib.utils.restricted import restricted
from irc_lib.utils.threadpool import Worker


class Error(Exception):
    pass


class CmdError(Error):
    def __init__(self, msg):
        Error.__init__(self)
        self.msg = msg

    def __str__(self):
        return 'Error: $R{msg}'.format(msg=self.msg)


class CmdSyntaxError(CmdError):
    def __init__(self, cmd, msg=''):
        CmdError.__init__(self, msg)
        self.cmd = cmd

    def __str__(self):
        return 'Syntax error: $B{cmd} {msg}'.format(cmd=self.cmd, msg=self.msg)


def maxlen(rows, field):
    return max([len(row[field]) for row in rows])


class MCPBotCmds(object):
    def __init__(self, bot, evt, dbh):
        self.bot = bot
        self.evt = evt
        self.dbh = dbh
        self.queries = None

    def reply(self, msg):
        self.bot.say(self.evt.sender, msg, dcc=self.evt.dcc)

    def process_cmd(self):
        try:
            with self.dbh.get_con() as db_con:
                self.queries = self.dbh.get_queries(db_con)
                cmd_func = getattr(self, 'cmd_%s' % self.evt.cmd, self.cmd_default)
                cmd_func()
        except CmdError as exc:
            self.reply(str(exc))

    def check_args(self, max_args, min_args=None, text=False, syntax=''):
        if min_args is None:
            min_args = max_args
        if text:
            msg_split = self.evt.msg.split(None, max_args - 1)
        else:
            msg_split = self.evt.msg.split(None)
        if min_args is not None and len(msg_split) < min_args or max_args is not None and len(msg_split) > max_args:
            raise CmdSyntaxError(self.evt.cmd, syntax)
        empty_args = max_args - len(msg_split)
        msg_split.extend([''] * empty_args)
        return msg_split

    def cmd_default(self):
        pass

    #================== Base chatting commands =========================
    @restricted(4)
    def cmd_say(self):
        self.say_command(self.bot.say)

    @restricted(4)
    def cmd_msg(self):
        self.say_command(self.bot.irc.privmsg)

    @restricted(4)
    def cmd_notice(self):
        self.say_command(self.bot.irc.notice)

    @restricted(4)
    def cmd_action(self):
        self.say_command(self.bot.ctcp.action)

    def say_command(self, say_func):
        target, outmsg = self.check_args(2, text=True, syntax='<target> <message>')

        say_func(target, outmsg)

    @restricted(4)
    def cmd_pub(self):
        outmsg, = self.check_args(1, text=True, syntax='<command>')

        # if command didn't come from a channel send it back to the sender instead
        if self.evt.chan is None:
            sender = self.evt.sender
        else:
            sender = self.evt.chan

        # due to moving the db lock MCPBotCmds isn't reentrant anymore, so we need to generate a new command instead of
        # just calling MCPBotCmds directly
        self.bot.process_msg(sender, self.evt.sender, outmsg)

    #================== Getters classes ================================
    def cmd_gcc(self):
        """$Bgcc <classname>$N              : Get Client Class."""
        self.get_class('client')

    def cmd_gsc(self):
        """$Bgsc <classname>$N              : Get Server Class."""
        self.get_class('server')

    def cmd_gc(self):
        self.get_class('client')
        self.get_class('server')

    def get_class(self, side):
        search_class, = self.check_args(1, syntax='<classname>')

        self.reply("$B[ GET %s CLASS ]" % side.upper())

        class_rows = self.queries.get_classes(search_class, side)

        if not class_rows:
            self.reply(" No result for $R%s" % search_class)
        else:
            for class_row in class_rows:
                self.reply(" Side        : $B%s" % side)
                self.reply(" Name        : $B%s" % class_row['name'])
                self.reply(" Notch       : $B%s" % class_row['notch'])
                self.reply(" Super       : $B%s" % class_row['supername'])

                const_rows = self.queries.get_constructors(search_class, side)
                for const_row in const_rows:
                    self.reply(" Constructor : $B%s$N | $B%s$N" % (const_row['sig'], const_row['notchsig']))

    #================== Getters members ================================
    def cmd_gcm(self):
        """$Bgcm [classname.]<methodname>$N : Get Client Method."""
        self.get_member('client', 'methods')

    def cmd_gsm(self):
        """$Bgsm [classname.]<methodname>$N : Get Server Method."""
        self.get_member('server', 'methods')

    def cmd_gm(self):
        self.get_member('client', 'methods')
        self.get_member('server', 'methods')

    def cmd_gcf(self):
        """$Bgcf [classname.]<fieldname>$N  : Get Client Field."""
        self.get_member('client', 'fields')

    def cmd_gsf(self):
        """$Bgsf [classname.]<fieldname>$N  : Get Server Field."""
        self.get_member('server', 'fields')

    def cmd_gf(self):
        self.get_member('client', 'fields')
        self.get_member('server', 'fields')

    def get_member(self, side, etype):
        member, sname = self.check_args(2, min_args=1, syntax='[<classname>.]<membername> [signature]')

        split_member = member.rsplit('.', 1)
        if len(split_member) > 1:
            cname = split_member[0]
            mname = split_member[1]
        else:
            cname = None
            mname = split_member[0]

        self.reply("$B[ GET %s %s ]" % (side.upper(), etype.upper()))

        if self.evt.dcc:
            lowlimit = 10
            highlimit = 999
        else:
            lowlimit = 1
            highlimit = 10

        rows = self.queries.get_member(cname, mname, sname, side, etype)

        if not rows:
            self.reply(" No result for $R%s" % self.evt.msg)
        elif len(rows) > highlimit:
            self.reply(" $BVERY$N ambiguous request $R%s" % self.evt.msg)
            self.reply(" Found %s results" % len(rows))
            self.reply(" Too many to display")
        elif highlimit >= len(rows) > lowlimit:
            self.reply(" Ambiguous request $R%s" % self.evt.msg)
            self.reply(" Found %s results" % len(rows))
            l_name = maxlen(rows, 'fullname')
            l_notch = maxlen(rows, 'fullnotch') + 2
            l_searge = maxlen(rows, 'searge') + 2
            for row in rows:
                p_name = (row['fullname']).ljust(l_name)
                p_notch = ('[%s]' % row['fullnotch']).ljust(l_notch)
                p_searge = ('[%s]' % row['searge']).ljust(l_searge)
                self.reply(" %s %s %s %s %s" % (p_searge, p_name, p_notch, row['sig'], row['notchsig']))
        else:
            for row in rows:
                self.reply(" Side        : $B%s" % side)
                self.reply(" Name        : $B%s" % row['fullname'])
                self.reply(" Notch       : $B%s" % row['fullnotch'])
                self.reply(" Searge      : $B%s" % row['searge'])
                self.reply(" Type/Notch  : $B%s$N | $B%s$N" % (row['sig'], row['notchsig']))
                if row['desc']:
                    self.reply(" Description : %s" % row['desc'])

    #====================== Search commands ============================
    def cmd_search(self):
        """$Bsearch <pattern>$N  : Search for a pattern."""
        search_str, = self.check_args(1, syntax='<name>')

        self.reply("$B[ SEARCH ]")

        if self.evt.dcc:
            highlimit = 100
        else:
            highlimit = 10

        rows = {'classes': None, 'fields': None, 'methods': None}

        for side in ['client', 'server']:
            rows['classes'] = self.queries.search_class(search_str, side)
            for etype in ['fields', 'methods']:
                rows[etype] = self.queries.search_member(search_str, side, etype)

            if not rows['classes']:
                self.reply(" [%s][  CLASS] No results" % side.upper())
            elif len(rows['classes']) > highlimit:
                self.reply(" [%s][  CLASS] Too many results : %d" % (side.upper(), len(rows['classes'])))
            else:
                l_name = maxlen(rows, 'name')
                l_notch = maxlen(rows, 'notch')
                for row in rows['classes']:
                    p_name = (row['name']).ljust(l_name)
                    p_notch = (row['notch']).ljust(l_notch)
                    self.reply(" [%s][  CLASS] %s %s" % (side.upper(), p_name, p_notch))

            for etype in ['fields', 'methods']:
                if not rows[etype]:
                    self.reply(" [%s][%7s] No results" % (side.upper(), etype.upper()))
                elif len(rows[etype]) > highlimit:
                    self.reply(" [%s][%7s] Too many results : %d" % (side.upper(), etype.upper(), len(rows[etype])))
                else:
                    l_name = maxlen(rows, 'fullname')
                    l_notch = maxlen(rows, 'fullnotch') + 2
                    for row in rows[etype]:
                        p_name = (row['fullname']).ljust(l_name)
                        p_notch = ('[%s]' % row['fullnotch']).ljust(l_notch)
                        self.reply(" [%s][%7s] %s %s %s %s" % (side.upper(), etype.upper(), p_name, p_notch,
                            row['sig'], row['notchsig']))

    #====================== Setters for members ========================
    def cmd_scm(self):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.set_member('client', 'methods')

    def cmd_scf(self):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.set_member('client', 'fields')

    def cmd_ssm(self):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.set_member('server', 'methods')

    def cmd_ssf(self):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.set_member('server', 'fields')

    def cmd_fscm(self):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.set_member('client', 'methods', forced=True)

    def cmd_fscf(self):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.set_member('client', 'fields', forced=True)

    def cmd_fssm(self):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.set_member('server', 'methods', forced=True)

    def cmd_fssf(self):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.set_member('server', 'fields', forced=True)

    def set_member(self, side, etype, forced=False):
        member, newname, newdesc = self.check_args(3, min_args=2, text=True,
                                                   syntax='<membername> <newname> [newdescription]')

        self.reply("$B[ SET %s %s ]" % (side.upper(), etype.upper()))

        if forced:
            self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE")

        # WE CHECK WE ONLY HAVE ONE RESULT
        rows = self.queries.get_member_searge(member, side, etype)
        if not rows:
            self.reply(" No result for $R%s" % member)
            return
        elif len(rows) > 1:
            self.reply(" Ambiguous request $R%s" % member)
            self.reply(" Found %s results" % len(rows))
            l_name = maxlen(rows, 'fullname')
            l_notch = maxlen(rows, 'fullnotch') + 2
            for row in rows:
                p_name = (row['fullname']).ljust(l_name)
                p_notch = ('[%s]' % row['fullnotch']).ljust(l_notch)
                self.reply(" %s %s %s" % (p_name, p_notch, row['sig']))
            return
        row = rows[0]

        if not forced:
            if row['searge'] != row['name']:
                raise CmdError("Trying to rename an already named member")

        self.queries.check_member_name(newname, side, etype, forced)

        if not newdesc and not row['desc']:
            newdesc = None
        elif not newdesc:
            newdesc = row['desc']
        elif newdesc == 'None':
            newdesc = None

        self.queries.update_member(member, newname, newdesc, side, etype, self.evt.sender, forced, self.evt.cmd)
        self.reply("Name     : $B%s => %s" % (row['name'], newname))
        self.reply("$BOld desc$N : %s" % row['desc'])
        self.reply("$BNew desc$N : %s" % newdesc)

    #======================= Port mappings =============================
    @restricted(2)
    def cmd_pcm(self):
        self.port_member('client', 'methods')

    @restricted(2)
    def cmd_pcf(self):
        self.port_member('client', 'fields')

    @restricted(2)
    def cmd_psm(self):
        self.port_member('server', 'methods')

    @restricted(2)
    def cmd_psf(self):
        self.port_member('server', 'fields')

    @restricted(2)
    def cmd_fpcm(self):
        self.port_member('client', 'methods', forced=True)

    @restricted(2)
    def cmd_fpcf(self):
        self.port_member('client', 'fields', forced=True)

    @restricted(2)
    def cmd_fpsm(self):
        self.port_member('server', 'methods', forced=True)

    @restricted(2)
    def cmd_fpsf(self):
        self.port_member('server', 'fields', forced=True)

    def port_member(self, side, etype, forced=False):
        origin, target = self.check_args(2, syntax='<origin_member> <target_member>')

        self.reply("$B[ PORT %s %s ]" % (side.upper(), etype.upper()))

        if side == 'client':
            target_side = 'server'
        else:
            target_side = 'client'

        if forced:
            self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE")

        # WE CHECK WE ONLY HAVE ONE RESULT
        rows = self.queries.get_member_searge(origin, side, etype)
        if not rows:
            self.reply(" No result for $R%s" % origin)
            return
        elif len(rows) > 1:
            self.reply(" Ambiguous request $R%s" % origin)
            self.reply(" Found %s results" % len(rows))
            l_name = maxlen(rows, 'fullname')
            l_notch = maxlen(rows, 'fullnotch') + 2
            for row in rows:
                p_name = (row['fullname']).ljust(l_name)
                p_notch = ('[%s]' % row['fullnotch']).ljust(l_notch)
                self.reply(" %s %s %s" % (p_name, p_notch, row['sig']))
            return
        src_row = rows[0]
        newname = src_row['name']
        newdesc = src_row['desc']

        # DO THE SAME FOR OTHER SIDE
        rows = self.queries.get_member_searge(target, target_side, etype)
        if not rows:
            self.reply(" No result for $R%s" % target)
            return
        elif len(rows) > 1:
            self.reply(" Ambiguous request $R%s" % target)
            self.reply(" Found %s results" % len(rows))
            l_name = maxlen(rows, 'fullname')
            l_notch = maxlen(rows, 'fullnotch') + 2
            for row in rows:
                p_name = (row['fullname']).ljust(l_name)
                p_notch = ('[%s]' % row['fullnotch']).ljust(l_notch)
                self.reply(" %s %s %s" % (p_name, p_notch, row['sig']))
            return
        tgt_row = rows[0]

        self.queries.check_member_name(newname, target_side, etype, forced)

        if not forced:
            if tgt_row['searge'] != tgt_row['name']:
                raise CmdError("Trying to rename an already named member")

        self.queries.update_member(target, newname, newdesc, target_side, etype, self.evt.sender, forced, self.evt.cmd)
        self.reply("%s     : $B%s => %s" % (side, origin, target))

    #======================= Mapping info ==============================
    @restricted(2)
    def cmd_icm(self):
        self.log_member('client', 'methods')

    @restricted(2)
    def cmd_icf(self):
        self.log_member('client', 'fields')

    @restricted(2)
    def cmd_ism(self):
        self.log_member('server', 'methods')

    @restricted(2)
    def cmd_isf(self):
        self.log_member('server', 'fields')

    def log_member(self, side, etype):
        member, = self.check_args(1, syntax='<member>')

        self.reply("$B[ GET CHANGES %s %s ]" % (side.upper(), etype.upper()))

        rows = self.queries.log_member(member, side, etype)

        if not rows:
            self.reply(" No result for $R%s" % self.evt.msg)
        else:
            for row in rows:
                self.reply("[%s, %s] %s: %s -> %s" % (row['mcpversion'], row['timestamp'], row['nick'], row['oldname'],
                    row['newname']))

    #====================== Revert changes =============================
    @restricted(2)
    def cmd_rcm(self):
        self.revert_member('client', 'methods')

    @restricted(2)
    def cmd_rcf(self):
        self.revert_member('client', 'fields')

    @restricted(2)
    def cmd_rsm(self):
        self.revert_member('server', 'methods')

    @restricted(2)
    def cmd_rsf(self):
        self.revert_member('server', 'fields')

    def revert_member(self, side, etype):
        member, = self.check_args(1, syntax='<member>')

        self.reply("$B[ REVERT %s %s ]" % (side.upper(), etype.upper()))

        self.queries.revert_member(member, side, etype)
        self.reply(" Reverted changes to $B%s" % member)

    #====================== Log Methods ================================
    def cmd_getlog(self):
        full_log, = self.check_args(1, min_args=0, syntax='[full]')
        if full_log.lower() == 'full':
            full_log = True
        else:
            full_log = False

        if not self.bot.debug:
            if not self.evt.dcc:
                self.reply("$BPlease use DCC for getlog")
                return

        self.reply("$B[ LOGS ]")

        for side in ['client', 'server']:
            for etype in ['methods', 'fields']:
                rows = self.queries.get_log(side, etype)
                if rows:
                    l_nick = maxlen(rows, 'nick')
                    l_searge = maxlen(rows, 'searge')
                    l_name = maxlen(rows, 'name')

                    for forcedstatus in [0, 1]:
                        for row in rows:
                            if row['forced'] == forcedstatus:
                                p_nick = (row['nick']).ljust(l_nick)
                                p_searge = (row['searge']).ljust(l_searge)
                                p_name = (row['name']).ljust(l_name)
                                p_index = re.search('[0-9]+', row['searge']).group()
                                if full_log:
                                    self.reply("+ %s, %s, %s" % (row['timestamp'], row['nick'], row['cmd']))
                                    self.reply("  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), p_searge,
                                        p_name, row['newname']))
                                    self.reply("  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), p_searge,
                                        row['desc'], row['newdesc']))
                                else:
                                    self.reply("+ %s, %s [%s%s][%5s][%4s] %s => %s" % (row['timestamp'], p_nick,
                                        side[0].upper(), etype[0].upper(), p_index, row['cmd'], p_name, row['newname']))

    @restricted(3)
    def cmd_commit(self):
        self.db_commit()

    @restricted(4)
    def cmd_fcommit(self):
        self.db_commit(forced=True)

    def db_commit(self, forced=False):
        self.check_args(0)

        self.reply("$B[ COMMIT ]")

        nentries = self.queries.db_commit(forced)
        if nentries:
            self.queries.add_commit(self.evt.sender)
            self.reply(" Committed %d entries" % nentries)
        else:
            self.reply(" No new entries to commit")

    @restricted(3)
    def cmd_altcsv(self):
        self.check_args(0)

        self.reply("$B[ ALTCSV ]")

        mcpversion = self.queries.get_mcpversion()
        if self.bot.debug:
            trgdir = 'devconf'
        else:
            trgdir = '/home/mcpfiles/mcprolling_%s/mcp/conf' % mcpversion

        self.write_csvs(trgdir)
        self.reply("New CSVs exported for MCP %s" % mcpversion)

    @restricted(2)
    def cmd_testcsv(self):
        self.check_args(0)

        self.reply("$B[ TESTCSV ]")

        mcpversion = self.queries.get_mcpversion()
        if self.bot.debug:
            trgdir = 'devconf'
        else:
            trgdir = '/home/mcpfiles/mcptest'

        self.write_csvs(trgdir)
        self.reply("Test CSVs for MCP %s exported: http://mcp.ocean-labs.de/files/mcptest/" % mcpversion)

    def write_csvs(self, trgdir):
        methodswriter = csv.DictWriter(open('%s/methods.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
        methodswriter.writeheader()
        rows = self.queries.csv_member('methods')
        for row in rows:
            methodswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'],
                                    'desc': row['desc']})

        fieldswriter = csv.DictWriter(open('%s/fields.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
        fieldswriter.writeheader()
        rows = self.queries.csv_member('fields')
        for row in rows:
            fieldswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'],
                                   'desc': row['desc']})

    #====================== Whitelist Handling =========================
    @restricted(0)
    def cmd_addwhite(self):
        nick, level = self.check_args(2, min_args=1, syntax='<nick> [level]')
        if level:
            try:
                level = int(level)
            except ValueError:
                raise CmdSyntaxError(self.evt.cmd, '<nick> [level]')
        else:
            level = 4

        self.reply("$B[ WHITELIST ]")

        if level > 4:
            raise CmdError("Max level is 4")
        if level >= self.bot.whitelist[self.evt.sender]:
            raise CmdError("You don't have the rights to do that")

        self.bot.add_whitelist(nick, level)
        self.reply("Added %s with level %d" % (nick, level))

    @restricted(0)
    def cmd_rmwhite(self):
        nick, = self.check_args(1, syntax='<nick>')

        self.reply("$B[ WHITELIST ]")

        if nick in self.bot.whitelist and self.bot.whitelist[nick] >= self.bot.whitelist[self.evt.sender]:
            raise CmdError("You don't have the rights to do that")

        try:
            self.bot.del_whitelist(nick)
        except KeyError:
            raise CmdError("%s not found" % nick)
        self.reply("Removed %s" % nick)

    @restricted(0)
    def cmd_getwhite(self):
        self.check_args(0)

        self.reply("$B[ WHITELIST ]")

        self.reply(str(self.bot.whitelist))

    @restricted(4)
    def cmd_savewhite(self):
        self.check_args(0)

        self.reply("$B[ WHITELIST ]")

        self.bot.save_whitelist()
        self.reply("Whitelist saved")

    @restricted(4)
    def cmd_loadwhite(self):
        self.check_args(0)

        self.reply("$B[ WHITELIST ]")

        self.bot.load_whitelist()
        self.reply("Whitelist loaded")

    #====================== Misc commands ==============================
    def cmd_dcc(self):
        """$Bdcc$N : Starts a dcc session. Faster and not under the flood protection."""
        self.check_args(0)

        self.bot.dcc.dcc(self.evt.sender)

    @restricted(4)
    def cmd_kick(self):
        chan, nick, comment = self.check_args(3, min_args=2, text=True, syntax='<channel> <target> [message]')

        if comment:
            self.bot.irc.kick(chan, nick, comment)
        else:
            self.bot.irc.kick(chan, nick)

    @restricted(5)
    def cmd_rawcmd(self):
        outmsg, = self.check_args(1, text=True, syntax='<command>')

        self.bot.irc.rawcmd(outmsg)

    def cmd_help(self):
        self.check_args(0)

        self.reply("$B[ HELP ]")

        self.reply("For help, please check : http://mcp.ocean-labs.de/index.php/MCPBot")

    def cmd_status(self):
        full_status, = self.check_args(1, min_args=0, syntax='[full]')
        if full_status.lower() == 'full':
            full_status = True
        else:
            full_status = False

        self.reply("$B[ STATUS ]")

        row = self.queries.status()
        self.reply(" MCP    : $B%s" % row['mcpversion'])
        self.reply(" Bot    : $B%s" % row['botversion'])
        self.reply(" Client : $B%s" % row['clientversion'])
        self.reply(" Server : $B%s" % row['serverversion'])

        if full_status:
            for side in ['client', 'server']:
                for etype in ['methods', 'fields']:
                    row = self.queries.status_members(side, etype)
                    if row['total']:
                        percent = float(row['ren']) / float(row['total']) * 100
                    else:
                        percent = 0.
                    self.reply(" [%s][%7s] : T $B%4d$N | R $B%4d$N | U $B%4d$N | $B%5.2f%%$N" % (
                        side[0].upper(), etype.upper(), row['total'], row['ren'], row['urn'], percent))

    @restricted(4)
    def cmd_listthreads(self):
        self.check_args(0)

        self.reply("$B[ THREADS ]")

        threads = threading.enumerate()
        l_name = max([len(i.name) for i in threads])

        for thread in threads:
            p_name = str(thread.name).ljust(l_name)
            if isinstance(thread, Worker):
                line = '%s %4d %4d %4d' % (p_name, thread.ncalls, thread.nscalls, thread.nfcalls)
            else:
                line = '%s %4d %4d %4d' % (p_name, 0, 0, 0)
            self.reply(line)

        nthreads = len(threads)
        if nthreads == self.bot.nthreads + 1:
            self.reply(" All threads up and running")
        else:
            self.reply(" Found only $R%d$N threads $BThere is a problem!" % (nthreads - 1))

    @restricted(4)
    def cmd_listdcc(self):
        self.check_args(0)

        self.reply("$B[ DCC USERS ]")

        self.reply(str(self.bot.dcc.sockets.keys()))

    def cmd_todo(self):
        search_side, = self.check_args(1, syntax='<client|server>')

        if search_side not in ['client', 'server']:
            raise CmdSyntaxError(self.evt.cmd, '<client|server>')

        self.reply("$B[ TODO %s ]" % search_side.upper())

        rows = self.queries.todo(search_side)
        for row in rows:
            if row['memberst']:
                percent = float(row['membersr']) / float(row['memberst']) * 100.0
            else:
                percent = 0.
            self.reply(" %s : $B%2d$N [ T $B%3d$N | R $B%3d$N | $B%5.2f%%$N ] " % (
                row['name'].ljust(20), row['membersu'], row['memberst'], row['membersr'], percent))
