import threading

from irc_lib.event import Event
from irc_lib.utils.restricted import restricted
from irc_lib.utils.ThreadPool import Worker
from mcpbotprocess import MCPBotProcess


class MCPBotCmds(object):
    def __init__(self, bot, ev):
        self.bot = bot
        self.ev = ev
        self.process = None

    def reply(self, msg):
        self.bot.say(self.ev.sender, msg)

    def process_cmd(self):
        with self.bot.db.get_db() as db:
            self.process = MCPBotProcess(self, db)
            getattr(self, 'cmd_%s' % self.ev.cmd, self.cmd_Default)()

    def check_args(self, max_args, min_args=None, text=False, syntax=''):
        if syntax:
            syntax = ' ' + syntax
        if min_args is None:
            min_args = max_args
        if text:
            msg_split = self.ev.msg.split(None, max_args - 1)
        else:
            msg_split = self.ev.msg.split(None)
        if min_args is not None and len(msg_split) < min_args or max_args is not None and len(msg_split) > max_args:
            print msg_split
            raise Exception(' Syntax error: $B{cmd}{syntax}'.format(cmd=self.ev.cmd, syntax=syntax))
        empty_args = max_args - len(msg_split)
        msg_split.extend([''] * empty_args)
        print msg_split
        return msg_split

    def cmd_Default(self):
        pass

    #================== Base chatting commands =========================
    @restricted(4)
    def cmd_say(self):
        target, outmsg = self.check_args(2, text=True, syntax='<target> <message>')

        self.bot.say(target, outmsg)

    @restricted(4)
    def cmd_msg(self):
        target, outmsg = self.check_args(2, text=True, syntax='<target> <message>')

        self.bot.irc.privmsg(target, outmsg)

    @restricted(4)
    def cmd_notice(self):
        target, outmsg = self.check_args(2, text=True, syntax='<target> <message>')

        self.bot.irc.notice(target, outmsg)

    @restricted(4)
    def cmd_action(self):
        target, outmsg = self.check_args(2, text=True, syntax='<target> <message>')

        self.bot.ctcp.action(target, outmsg)

    @restricted(4)
    def cmd_pub(self):
        outcmd, outmsg = self.check_args(2, min_args=1, text=True, syntax='<command>')

        outcmd = outcmd.lower()
        if len(outcmd) > 1 and outcmd[0] == self.bot.controlchar:
            outcmd = outcmd[1:]

        if self.ev.chan is None:
            sender = self.ev.senderfull
        else:
            sender = self.ev.chan

        outev = Event(sender, outcmd, self.ev.chan, outmsg, 'CMD')
        MCPBotCmds(self.bot, outev).process_cmd()

    #===================================================================

    #================== Getters classes ================================
    def cmd_gcc(self):
        """$Bgcc <classname>$N              : Get Client Class."""
        self.process.getClass('client')

    def cmd_gsc(self):
        """$Bgsc <classname>$N              : Get Server Class."""
        self.process.getClass('server')

    def cmd_gc(self):
        self.process.getClass('client')
        self.process.getClass('server')

    #===================================================================

    #================== Getters members ================================
    def cmd_gcm(self):
        """$Bgcm [classname.]<methodname>$N : Get Client Method."""
        self.process.outputMembers('client', 'methods')

    def cmd_gsm(self):
        """$Bgsm [classname.]<methodname>$N : Get Server Method."""
        self.process.outputMembers('server', 'methods')

    def cmd_gm(self):
        self.process.outputMembers('client', 'methods')
        self.process.outputMembers('server', 'methods')

    def cmd_gcf(self):
        """$Bgcf [classname.]<fieldname>$N  : Get Client Field."""
        self.process.outputMembers('client', 'fields')

    def cmd_gsf(self):
        """$Bgsf [classname.]<fieldname>$N  : Get Server Field."""
        self.process.outputMembers('server', 'fields')

    def cmd_gf(self):
        self.process.outputMembers('client', 'fields')
        self.process.outputMembers('server', 'fields')

    #===================================================================

    #====================== Search commands ============================
    def cmd_search(self):
        """$Bsearch <pattern>$N  : Search for a pattern."""
        self.process.search()

    #===================================================================

    #====================== Setters for members ========================
    def cmd_scm(self):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.process.setMember('client', 'methods', forced=False)

    def cmd_scf(self):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.process.setMember('client', 'fields', forced=False)

    def cmd_ssm(self):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.process.setMember('server', 'methods', forced=False)

    def cmd_ssf(self):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.process.setMember('server', 'fields', forced=False)

    def cmd_fscm(self):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.process.setMember('client', 'methods', forced=True)

    def cmd_fscf(self):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.process.setMember('client', 'fields', forced=True)

    def cmd_fssm(self):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.process.setMember('server', 'methods', forced=True)

    def cmd_fssf(self):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.process.setMember('server', 'fields', forced=True)

    #===================================================================

    #======================= Port mappings =============================
    @restricted(2)
    def cmd_pcm(self):
        self.process.portMember('client', 'methods', forced=False)

    @restricted(2)
    def cmd_pcf(self):
        self.process.portMember('client', 'fields', forced=False)

    @restricted(2)
    def cmd_psm(self):
        self.process.portMember('server', 'methods', forced=False)

    @restricted(2)
    def cmd_psf(self):
        self.process.portMember('server', 'fields', forced=False)

    @restricted(2)
    def cmd_fpcm(self):
        self.process.portMember('client', 'methods', forced=True)

    @restricted(2)
    def cmd_fpcf(self):
        self.process.portMember('client', 'fields', forced=True)

    @restricted(2)
    def cmd_fpsm(self):
        self.process.portMember('server', 'methods', forced=True)

    @restricted(2)
    def cmd_fpsf(self):
        self.process.portMember('server', 'fields', forced=True)

    #===================================================================

    #======================= Mapping info ==============================
    @restricted(2)
    def cmd_icm(self):
        self.process.infoChanges('client', 'methods')

    @restricted(2)
    def cmd_icf(self):
        self.process.infoChanges('client', 'fields')

    @restricted(2)
    def cmd_ism(self):
        self.process.infoChanges('server', 'methods')

    @restricted(2)
    def cmd_isf(self):
        self.process.infoChanges('server', 'fields')

    #===================================================================

    #====================== Revert changes =============================
    @restricted(2)
    def cmd_rcm(self):
        self.process.revertChanges('client', 'methods')

    @restricted(2)
    def cmd_rcf(self):
        self.process.revertChanges('client', 'fields')

    @restricted(2)
    def cmd_rsm(self):
        self.process.revertChanges('server', 'methods')

    @restricted(2)
    def cmd_rsf(self):
        self.process.revertChanges('server', 'fields')

    #===================================================================

    #====================== Log Methods ================================
    def cmd_getlog(self):
        self.process.getlog()

    @restricted(3)
    def cmd_commit(self):
        self.process.dbCommit(pushforced=False)

    @restricted(4)
    def cmd_fcommit(self):
        self.process.dbCommit(pushforced=True)

    @restricted(3)
    def cmd_altcsv(self):
        self.process.altCsv()

    @restricted(2)
    def cmd_testcsv(self):
        self.process.testCsv()

    #===================================================================

    #====================== Whitelist Handling =========================
    @restricted(0)
    def cmd_addwhite(self):
        nick, level = self.check_args(2, min_args=1, syntax='<nick> [level]')
        if level:
            try:
                level = int(level)
            except ValueError:
                raise Exception(' Syntax error: $B{cmd} <nick> [level]'.format(cmd=self.ev.cmd))
        else:
            level = 4

        if level > 4:
            self.reply("Max level is 4.")
            return
        if level >= self.bot.whitelist[self.ev.sender]:
            self.reply("You don't have the rights to do that.")
            return

        self.bot.addWhitelist(nick, level)
        self.reply("Added %s with level %d to whitelist" % (nick, level))

    @restricted(0)
    def cmd_rmwhite(self):
        nick, = self.check_args(1, syntax='<nick>')

        if nick in self.bot.whitelist and self.bot.whitelist[nick] >= self.bot.whitelist[self.ev.sender]:
            self.reply("You don't have the rights to do that.")
            return

        try:
            self.bot.rmWhitelist(nick)
        except KeyError:
            self.reply("User %s not found in the whitelist" % nick)
            return
        self.reply("User %s removed from the whitelist" % nick)

    @restricted(0)
    def cmd_getwhite(self):
        self.check_args(0)

        self.reply("Whitelist : %s" % self.bot.whitelist)

    @restricted(4)
    def cmd_savewhite(self):
        self.check_args(0)

        self.bot.saveWhitelist()

    @restricted(4)
    def cmd_loadwhite(self):
        self.check_args(0)

        self.bot.loadWhitelist()
    #===================================================================

    #====================== Misc commands ==============================
    def cmd_dcc(self):
        """$Bdcc$N : Starts a dcc session. Faster and not under the flood protection."""
        self.check_args(0)

        self.bot.dcc.dcc(self.ev.sender)

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
        self.process.status()

    @restricted(4)
    def cmd_listthreads(self):
        self.check_args(0)

        threads = threading.enumerate()
        self.reply("$B[ THREADS ]")
        maxthreadname = max([len(i.name) for i in threads])

        for t in threads:
            if isinstance(t, Worker):
                line = '%s %4d %4d %4d' % (str(t.name).ljust(maxthreadname), t.ncalls, t.nscalls, t.nfcalls)
            else:
                line = '%s %4d %4d %4d' % (str(t.name).ljust(maxthreadname), 0, 0, 0)
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
        self.process.todo()
