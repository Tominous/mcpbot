import threading

from irc_lib.utils.restricted import restricted
from irc_lib.utils.ThreadPool import Worker
from mcpbotprocess import MCPBotProcess


class MCPBotCmds(object):
    def __init__(self, bot, db_name):
        self.bot = bot
        self.process = MCPBotProcess(bot, db_name)
        self.say = self.bot.say

    def cmdDefault(self, sender, chan, cmd, msg):
        pass

    #================== Base chatting commands =========================
    @restricted(4)
    def cmd_say(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.say(target, outmsg)

    @restricted(4)
    def cmd_msg(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.bot.irc.privmsg(target, outmsg)

    @restricted(4)
    def cmd_notice(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.bot.irc.notice(target, outmsg)

    @restricted(4)
    def cmd_action(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.bot.ctcp.action(target, outmsg)

    @restricted(4)
    def cmd_pub(self, sender, chan, cmd, msg):
        msg = msg.lstrip()
        if not msg:
            return
        if msg[0] == self.bot.controlchar:
            msg = msg[1:]
        msg_split = msg.strip().split(None, 1)
        if not len(msg_split):
            self.say(sender, " Syntax error: $B%s <command>$N" % cmd)
            return
        outcmd = msg_split[0].lower()
        if len(msg_split) > 1:
            outmsg = msg_split[1]
        else:
            outmsg = ''

        if outcmd in ['ssf, ssm, scf, scm']:
            self.say(sender, 'No public setters !')
            return

        cmd_func = getattr(self, 'cmd_%s' % outcmd, self.cmdDefault)
        cmd_func(chan, chan, outcmd, outmsg)

    #===================================================================

    #================== Getters classes ================================
    def cmd_gcc(self, sender, chan, cmd, msg):
        """$Bgcc <classname>$N              : Get Client Class."""
        self.process.getClass(sender, chan, cmd, msg, 'client')

    def cmd_gsc(self, sender, chan, cmd, msg):
        """$Bgsc <classname>$N              : Get Server Class."""
        self.process.getClass(sender, chan, cmd, msg, 'server')

    def cmd_gc(self, sender, chan, cmd, msg):
        self.process.getClass(sender, chan, cmd, msg, 'client')
        self.process.getClass(sender, chan, cmd, msg, 'server')

    #===================================================================

    #================== Getters members ================================
    def cmd_gcm(self, sender, chan, cmd, msg):
        """$Bgcm [classname.]<methodname>$N : Get Client Method."""
        self.process.outputMembers(sender, chan, cmd, msg, 'client', 'methods')

    def cmd_gsm(self, sender, chan, cmd, msg):
        """$Bgsm [classname.]<methodname>$N : Get Server Method."""
        self.process.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmd_gm(self, sender, chan, cmd, msg):
        self.process.outputMembers(sender, chan, cmd, msg, 'client', 'methods')
        self.process.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmd_gcf(self, sender, chan, cmd, msg):
        """$Bgcf [classname.]<fieldname>$N  : Get Client Field."""
        self.process.outputMembers(sender, chan, cmd, msg, 'client', 'fields')

    def cmd_gsf(self, sender, chan, cmd, msg):
        """$Bgsf [classname.]<fieldname>$N  : Get Server Field."""
        self.process.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    def cmd_gf(self, sender, chan, cmd, msg):
        self.process.outputMembers(sender, chan, cmd, msg, 'client', 'fields')
        self.process.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    #===================================================================

    #====================== Search commands ============================
    def cmd_search(self, sender, chan, cmd, msg):
        """$Bsearch <pattern>$N  : Search for a pattern."""
        self.process.search(sender, chan, cmd, msg)

    #===================================================================

    #====================== Setters for members ========================
    def cmd_scm(self, sender, chan, cmd, msg):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.process.setMember(sender, chan, cmd, msg, 'client', 'methods', forced=False)

    def cmd_scf(self, sender, chan, cmd, msg):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.process.setMember(sender, chan, cmd, msg, 'client', 'fields', forced=False)

    def cmd_ssm(self, sender, chan, cmd, msg):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.process.setMember(sender, chan, cmd, msg, 'server', 'methods', forced=False)

    def cmd_ssf(self, sender, chan, cmd, msg):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.process.setMember(sender, chan, cmd, msg, 'server', 'fields', forced=False)

    def cmd_fscm(self, sender, chan, cmd, msg):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.process.setMember(sender, chan, cmd, msg, 'client', 'methods', forced=True)

    def cmd_fscf(self, sender, chan, cmd, msg):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.process.setMember(sender, chan, cmd, msg, 'client', 'fields', forced=True)

    def cmd_fssm(self, sender, chan, cmd, msg):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.process.setMember(sender, chan, cmd, msg, 'server', 'methods', forced=True)

    def cmd_fssf(self, sender, chan, cmd, msg):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.process.setMember(sender, chan, cmd, msg, 'server', 'fields', forced=True)

    #===================================================================

    #======================= Port mappings =============================
    @restricted(2)
    def cmd_pcm(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'client', 'methods', forced=False)

    @restricted(2)
    def cmd_pcf(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'client', 'fields', forced=False)

    @restricted(2)
    def cmd_psm(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'server', 'methods', forced=False)

    @restricted(2)
    def cmd_psf(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'server', 'fields', forced=False)

    @restricted(2)
    def cmd_fpcm(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'client', 'methods', forced=True)

    @restricted(2)
    def cmd_fpcf(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'client', 'fields', forced=True)

    @restricted(2)
    def cmd_fpsm(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'server', 'methods', forced=True)

    @restricted(2)
    def cmd_fpsf(self, sender, chan, cmd, msg):
        self.process.portMember(sender, chan, cmd, msg, 'server', 'fields', forced=True)

    #===================================================================

    #======================= Mapping info ==============================
    @restricted(2)
    def cmd_icm(self, sender, chan, cmd, msg):
        self.process.infoChanges(sender, chan, cmd, msg, 'client', 'methods')

    @restricted(2)
    def cmd_icf(self, sender, chan, cmd, msg):
        self.process.infoChanges(sender, chan, cmd, msg, 'client', 'fields')

    @restricted(2)
    def cmd_ism(self, sender, chan, cmd, msg):
        self.process.infoChanges(sender, chan, cmd, msg, 'server', 'methods')

    @restricted(2)
    def cmd_isf(self, sender, chan, cmd, msg):
        self.process.infoChanges(sender, chan, cmd, msg, 'server', 'fields')

    #===================================================================

    #====================== Revert changes =============================
    @restricted(2)
    def cmd_rcm(self, sender, chan, cmd, msg):
        self.process.revertChanges(sender, chan, cmd, msg, 'client', 'methods')

    @restricted(2)
    def cmd_rcf(self, sender, chan, cmd, msg):
        self.process.revertChanges(sender, chan, cmd, msg, 'client', 'fields')

    @restricted(2)
    def cmd_rsm(self, sender, chan, cmd, msg):
        self.process.revertChanges(sender, chan, cmd, msg, 'server', 'methods')

    @restricted(2)
    def cmd_rsf(self, sender, chan, cmd, msg):
        self.process.revertChanges(sender, chan, cmd, msg, 'server', 'fields')

    #===================================================================

    #====================== Log Methods ================================
    def cmd_getlog(self, sender, chan, cmd, msg):
        self.process.getlog(sender, chan, cmd, msg)

    @restricted(3)
    def cmd_commit(self, sender, chan, cmd, msg):
        self.process.dbCommit(sender, chan, cmd, msg, pushforced=False)

    @restricted(4)
    def cmd_fcommit(self, sender, chan, cmd, msg):
        self.process.dbCommit(sender, chan, cmd, msg, pushforced=True)

    @restricted(3)
    def cmd_updatecsv(self, sender, chan, cmd, msg):
        self.process.dbCommit(sender, chan, cmd, msg, pushforced=False)
        self.process.updateCsv(sender, chan, cmd, msg)

    @restricted(4)
    def cmd_fupdatecsv(self, sender, chan, cmd, msg):
        self.process.dbCommit(sender, chan, cmd, msg, pushforced=True)
        self.process.updateCsv(sender, chan, cmd, msg)

    @restricted(3)
    def cmd_altcsv(self, sender, chan, cmd, msg):
        self.process.altCsv(sender, chan, cmd, msg)

    @restricted(2)
    def cmd_testcsv(self, sender, chan, cmd, msg):
        self.process.testCsv(sender, chan, cmd, msg)

    #===================================================================

    #====================== Whitelist Handling =========================
    @restricted(0)
    def cmd_addwhite(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 2)
        if len(msg_split) == 1:
            nick = msg_split[0]
            level = 4
        elif len(msg_split) == 2:
            nick = msg_split[0]
            try:
                level = int(msg_split[1])
            except ValueError:
                self.say(sender, "Syntax error: $B%s <nick> [level]" % cmd)
                return
        else:
            self.say(sender, "Syntax error: $B%s <nick> [level]" % cmd)
            return
        if level > 4:
            self.say(sender, "Max level is 4.")
            return
        if level >= self.bot.whitelist[sender]:
            self.say(sender, "You don't have the rights to do that.")
            return
        self.bot.addWhitelist(nick, level)
        self.say(sender, "Added %s with level %d to whitelist" % (nick, level))

    @restricted(0)
    def cmd_rmwhite(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) != 1:
            self.say(sender, "Syntax error: $B%s <nick>" % cmd)
            return
        nick = msg_split[0]

        if nick in self.bot.whitelist and self.bot.whitelist[nick] >= self.bot.whitelist[sender]:
            self.say(sender, "You don't have the rights to do that.")
            return

        try:
            self.bot.rmWhitelist(nick)
        except KeyError:
            self.say(sender, "User %s not found in the whitelist" % nick)
            return
        self.say(sender, "User %s removed from the whitelist" % nick)

    @restricted(0)
    def cmd_getwhite(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.say(sender, "Whitelist : %s" % self.bot.whitelist)

    @restricted(4)
    def cmd_savewhite(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.bot.saveWhitelist()

    @restricted(4)
    def cmd_loadwhite(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.bot.loadWhitelist()
    #===================================================================

    #====================== Misc commands ==============================
    def cmd_dcc(self, sender, chan, cmd, msg):
        """$Bdcc$N : Starts a dcc session. Faster and not under the flood protection."""
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.bot.dcc.dcc(sender)

    @restricted(4)
    def cmd_kick(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 2)
        if len(msg_split) < 2:
            self.say(sender, "Syntax error: $B%s <channel> <target> [message]" % cmd)
            return
        if len(msg_split) > 2:
            self.bot.irc.kick(msg_split[0], msg_split[1], msg_split[2])
        else:
            self.bot.irc.kick(msg_split[0], msg_split[1])

    @restricted(5)
    def cmd_rawcmd(self, sender, chan, cmd, msg):
        self.bot.irc.rawcmd(msg)

    def cmd_help(self, sender, chan, cmd, msg):
        self.say(sender, "$B[ HELP ]")
        self.say(sender, "For help, please check : http://mcp.ocean-labs.de/index.php/MCPBot")

    def cmd_status(self, sender, chan, cmd, msg):
        self.process.status(sender, chan, cmd, msg)

    @restricted(4)
    def cmd_listthreads(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return

        threads = threading.enumerate()
        self.say(sender, "$B[ THREADS ]")
        maxthreadname = max([len(i.name) for i in threads])

        for t in threads:
            if isinstance(t, Worker):
                line = '%s %4d %4d %4d' % (str(t.name).ljust(maxthreadname), t.ncalls, t.nscalls, t.nfcalls)
            else:
                line = '%s %4d %4d %4d' % (str(t.name).ljust(maxthreadname), 0, 0, 0)
            self.say(sender, line)

        nthreads = len(threads)
        if nthreads == self.bot.nthreads + 1:
            self.say(sender, " All threads up and running !")
        else:
            self.say(sender, " Found only $R%d$N threads ! $BThere is a problem !" % (nthreads - 1))

    @restricted(4)
    def cmd_listdcc(self, sender, chan, cmd, msg):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return

        self.say(sender, str(self.bot.dcc.sockets.keys()))

    def cmd_todo(self, sender, chan, cmd, msg):
        self.process.todo(sender, chan, cmd, msg)
