import sqlite3
from irc_lib.utils.restricted import restricted

class MCPBotCmds(object):
    def cmdDefault(self, sender, chan, cmd, msg):
        pass

    #================== Base chatting commands =========================
    @restricted
    def cmdSay(self, sender, chan, cmd, msg):
        self.say(msg.split()[0], ' '.join(msg.split()[1:]))

    @restricted
    def cmdMsg(self, sender, chan, cmd, msg):
        self.irc.privmsg(msg.split()[0], ' '.join(msg.split()[1:]))

    @restricted
    def cmdNotice(self, sender, chan, cmd, msg):
        self.irc.notice(msg.split()[0], ' '.join(msg.split()[1:]))

    @restricted
    def cmdAction(self, sender, chan, cmd, msg):
        self.ctcp.action(msg.split()[0], ' '.join(msg.split()[1:]))
    #===================================================================

    #================== Getters classes ================================
    @restricted
    def cmdGcc(self, sender, chan, cmd, msg):
        self.getClass(sender, chan, cmd, msg, 'client')

    @restricted
    def cmdGsc(self, sender, chan, cmd, msg):
        self.getClass(sender, chan, cmd, msg, 'server')

    @restricted
    def cmdGc(self, sender, chan, cmd, msg):
        self.getClass(sender, chan, cmd, msg, 'client')        
        self.getClass(sender, chan, cmd, msg, 'server')

    def getClass(self, sender, chan, cmd, msg, side):
        dbase = sqlite3.connect('database.db')
        c = dbase.cursor()
        c.execute("""SELECT c1.name, c1.notch, c2.name, c2.notch FROM classes c1 LEFT JOIN classes c2 ON c1.super = c2.id WHERE (c1.name = '%s' OR c1.notch = '%s') AND c1.side='%s'"""%(msg,msg,side))
        
        nrow = 0
        for row in c:
            self.say(sender, "=== GET CLASS %s ==="%side.upper())
            self.say(sender, "$BSide$N        : %s"%side)
            self.say(sender, "$BName$N        : %s"%row[0])
            self.say(sender, "$BNotch$N       : %s"%row[1])
            self.say(sender, "$BSuper$N       : %s"%row[2])
            nrow += 1

        if nrow == 0:
            self.say(sender, "=== GET CLASS %s ==="%side.upper())
            self.say(sender, "No result for %s"%msg)
            c.close()
            return

        c.execute("""SELECT m.signature FROM methods m WHERE (m.name = '%s' OR m.notch = '%s') AND m.side='%s'"""%(msg,msg,side))
        for row in c:
            self.say(sender, "$BConstructor$N : %s"%row[0])            

        c.close()
    #===================================================================
