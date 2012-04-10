import threading

from irc_lib.utils.restricted import restricted
from irc_lib.utils.threadpool import Worker
from mcpbotprocess import MCPBotProcess, SIDE_LOOKUP, CmdError, CmdSyntaxError


class MCPBotCmds(object):
    def __init__(self, bot, evt, dbh):
        self.bot = bot
        self.evt = evt
        self.dbh = dbh
        self.process = None

    def reply(self, msg):
        self.bot.say(self.evt.sender, msg)

    def process_cmd(self):
        try:
            with self.dbh.get_con() as db_con:
                self.process = MCPBotProcess(self, db_con)
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
        self.process.get_class(search_class, side)

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
        self.process.get_member(cname, mname, sname, side, etype)

    #====================== Search commands ============================
    def cmd_search(self):
        """$Bsearch <pattern>$N  : Search for a pattern."""
        search_str, = self.check_args(1, syntax='<name>')

        self.reply("$B[ SEARCH RESULTS ]")
        self.process.search(search_str)

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
        oldname, newname, newdesc = self.check_args(3, min_args=2, text=True, syntax='<membername> <newname> [newdescription]')

        self.reply("$B[ SET %s %s ]" % (side.upper(), etype.upper()))
        self.process.set_member(oldname, newname, newdesc, side, etype, forced)

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
        self.process.port_member(origin, target, side, etype, forced)

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
        self.process.log_member(member, side, etype)

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
        self.process.revert_member(member, side, etype)

    #====================== Log Methods ================================
    def cmd_getlog(self):
        full_log, = self.check_args(1, min_args=0, syntax='[full]')
        if full_log.lower() == 'full':
            full_log = True
        else:
            full_log = False

        self.reply("$B[ LOGS ]")
        self.process.get_log(full_log)

    @restricted(3)
    def cmd_commit(self):
        self.db_commit()

    @restricted(4)
    def cmd_fcommit(self):
        self.db_commit(forced=True)

    def db_commit(self, forced=False):
        self.check_args(0)

        self.reply("$B[ COMMIT ]")
        self.process.db_commit(forced)

    @restricted(3)
    def cmd_altcsv(self):
        self.check_args(0)

        self.process.alt_csv()

    @restricted(2)
    def cmd_testcsv(self):
        self.check_args(0)

        self.process.test_csv()

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

        if level > 4:
            raise CmdError("Max level is 4")
        if level >= self.bot.whitelist[self.evt.sender]:
            raise CmdError("You don't have the rights to do that")

        self.bot.add_whitelist(nick, level)
        self.reply("Added %s with level %d to whitelist" % (nick, level))

    @restricted(0)
    def cmd_rmwhite(self):
        nick, = self.check_args(1, syntax='<nick>')

        if nick in self.bot.whitelist and self.bot.whitelist[nick] >= self.bot.whitelist[self.evt.sender]:
            raise CmdError("You don't have the rights to do that.")

        try:
            self.bot.del_whitelist(nick)
        except KeyError:
            raise CmdError("User %s not found in the whitelist" % nick)
        self.reply("User %s removed from the whitelist" % nick)

    @restricted(0)
    def cmd_getwhite(self):
        self.check_args(0)

        self.reply("Whitelist : %s" % self.bot.whitelist)

    @restricted(4)
    def cmd_savewhite(self):
        self.check_args(0)

        self.bot.save_whitelist()

    @restricted(4)
    def cmd_loadwhite(self):
        self.check_args(0)

        self.bot.load_whitelist()

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
        self.process.status(full_status)

    @restricted(4)
    def cmd_listthreads(self):
        self.check_args(0)

        self.reply("$B[ THREADS ]")

        threads = threading.enumerate()
        maxthreadname = max([len(i.name) for i in threads])

        for thread in threads:
            if isinstance(thread, Worker):
                line = '%s %4d %4d %4d' % (str(thread.name).ljust(maxthreadname), thread.ncalls, thread.nscalls, thread.nfcalls)
            else:
                line = '%s %4d %4d %4d' % (str(thread.name).ljust(maxthreadname), 0, 0, 0)
            self.reply(line)

        nthreads = len(threads)
        if nthreads == self.bot.nthreads + 1:
            self.reply(" All threads up and running !")
        else:
            self.reply(" Found only $R%d$N threads ! $BThere is a problem !" % (nthreads - 1))

    @restricted(4)
    def cmd_listdcc(self):
        self.check_args(0)

        self.reply(str(self.bot.dcc.sockets.keys()))

    def cmd_todo(self):
        search_side, = self.check_args(1, syntax='<client|server>')

        if search_side not in SIDE_LOOKUP:
            raise CmdSyntaxError(self.evt.cmd, '<client|server>')

        self.reply("$B[ TODO %s ]" % search_side.upper())
        self.process.todo(search_side)
