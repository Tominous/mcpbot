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
    def cmdGcc(self, sender, chan, cmd, msg):
        self.getClass(sender, chan, cmd, msg, 'client')

    def cmdGsc(self, sender, chan, cmd, msg):
        self.getClass(sender, chan, cmd, msg, 'server')

    def cmdGc(self, sender, chan, cmd, msg):
        self.getClass(sender, chan, cmd, msg, 'client')        
        self.getClass(sender, chan, cmd, msg, 'server')

    def getClass(self, sender, chan, cmd, msg, side):
        dbase = sqlite3.connect('database.db')
        c = dbase.cursor()
        c.execute("""SELECT c1.name, c1.notch, c2.name, c2.notch 
                     FROM classes c1 LEFT JOIN classes c2 ON c1.super = c2.id 
                     WHERE (c1.name = ? OR c1.notch = ?) AND c1.side= ?""",
                     (msg,msg,side))
        
        nrow = 0
        for row in c:
            self.say(sender, "=== GET CLASS %s ==="%side.upper())
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s"%row[0])
            self.say(sender, " $BNotch$N       : %s"%row[1])
            self.say(sender, " $BSuper$N       : %s"%row[2])
            nrow += 1

        if nrow == 0:
            self.say(sender, "=== GET CLASS %s ==="%side.upper())
            self.say(sender, " No result for %s"%msg)
            c.close()
            return

        c.execute("""SELECT m.signature FROM methods m WHERE (m.name = ? OR m.notch = ?) AND m.side = ?""",(msg,msg,side))
        for row in c:
            self.say(sender, " $BConstructor$N : %s"%row[0])            

        c.close()
        dbase.close()
        
    #===================================================================

    #================== Getters members ================================
    def cmdGcm(self, sender, chan, cmd, msg):
        self.getMember(sender, chan, cmd, msg, 'client', 'method')

    def cmdGsm(self, sender, chan, cmd, msg):
        self.getMember(sender, chan, cmd, msg, 'server', 'method')

    def cmdGm(self, sender, chan, cmd, msg):
        self.getMember(sender, chan, cmd, msg, 'client', 'method')        
        self.getMember(sender, chan, cmd, msg, 'server', 'method')

    def cmdGcf(self, sender, chan, cmd, msg):
        self.getMember(sender, chan, cmd, msg, 'client', 'field')

    def cmdGsf(self, sender, chan, cmd, msg):
        self.getMember(sender, chan, cmd, msg, 'server', 'field')

    def cmdGf(self, sender, chan, cmd, msg):
        self.getMember(sender, chan, cmd, msg, 'client', 'field')        
        self.getMember(sender, chan, cmd, msg, 'server', 'field')

    def getMember(self, sender, chan, cmd, msg, side, etype):
        type_lookup = {'method':'func','field':'field'}
        dbase = sqlite3.connect('database.db')
        c = dbase.cursor()
        
        if '.' in msg:
            classname  = msg.split('.')[0]
            membername = msg.split('.')[1]
            c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch 
                         FROM %ss m LEFT JOIN classes c ON m.class = c.id
                         WHERE ((m.name LIKE ? ESCAPE '!') OR m.notch = ? OR m.decoded = ?) AND m.side = ? AND (c.name = ? OR c.notch = ?)"""%
                         etype,
                         ('%s!_%s!_%%'%(type_lookup[etype], membername), membername, membername, side, classname, classname))
        else:
            c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch 
                         FROM %ss m LEFT JOIN classes c ON m.class = c.id
                         WHERE ((m.name LIKE ? ESCAPE '!') OR m.notch = ? OR m.decoded = ?) AND m.side = ?"""%etype,
                         ('%s!_%s!_%%'%(type_lookup[etype], msg), msg, msg, side))
                     
        nrow = 0      
        for row in c:
            self.say(sender, "=== GET %s %s ==="%(etype.upper(),side.upper()))
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s"%row[2])
            self.say(sender, " $BNotch$N       : %s"%row[1])
            self.say(sender, " $BSearge$N      : %s"%row[0])
            self.say(sender, " $BType/Sig$N    : %s"%row[3])
            #self.say(sender, " $BNotchType$N   : %s"%row[4])            
            self.say(sender, " $BClass$N       : %s"%row[5])            
            nrow += 1

        if nrow == 0:
            self.say(sender, "=== GET %s %s ==="%(etype.upper(),side.upper()))
            self.say(sender, " No result for %s"%msg)
            c.close()
            return
            
        c.close()
        dbase.close()
        
    #===================================================================

    #====================== Whitelist Handling =========================
    @restricted
    def cmdAddwhite(self, sender, chan, cmd, msg):
        self.addWhitelist(msg)
        
    @restricted
    def cmdRmwhite(self, sender, chan, cmd, msg):
        self.rmWhitelist(msg)
    #===================================================================

    #====================== Misc commands ==============================
    @restricted
    def cmdExec(self, sender, chan, cmd, msg):
        try:
            print msg
            exec(msg) in self.globaldic, self.localdic
        except Exception as errormsg:
            self.printq.put ('ERROR : %s'%errormsg)
            self.say(sender, 'ERROR : %s'%errormsg)

