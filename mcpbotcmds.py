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
        
        rows = c.fetchall()
                
        for row in rows:
            self.say(sender, "=== GET CLASS %s ==="%side.upper())
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s"%row[0])
            self.say(sender, " $BNotch$N       : %s"%row[1])
            self.say(sender, " $BSuper$N       : %s"%row[2])

        if not rows:
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
            c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description
                         FROM %ss m LEFT JOIN classes c ON m.class = c.id
                         WHERE ((m.name LIKE ? ESCAPE '!') OR m.notch = ? OR m.decoded = ?) AND m.side = ? AND (c.name = ? OR c.notch = ?)"""%
                         etype,
                         ('%s!_%s!_%%'%(type_lookup[etype], membername), membername, membername, side, classname, classname))
        else:
            c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description
                         FROM %ss m LEFT JOIN classes c ON m.class = c.id
                         WHERE ((m.name LIKE ? ESCAPE '!') OR m.notch = ? OR m.decoded = ?) AND m.side = ?"""%etype,
                         ('%s!_%s!_%%'%(type_lookup[etype], msg), msg, msg, side))
        
        rows = c.fetchall()

        if len(rows) > 10:
            self.say(sender, "=== GET %s %s ==="%(etype.upper(),side.upper()))
            self.say(sender, " $BVERY$N ambiguous request $R'%s'$N"%msg)
            self.say(sender, " Found %s possible answers"%len(rows))        
            self.say(sender, " Not displaying any !")        
        elif 10 >= len(rows) > 1:
            self.say(sender, "=== GET %s %s ==="%(etype.upper(),side.upper()))
            self.say(sender, " Ambiguous request $R'%s'$N"%msg)
            self.say(sender, " Found %s possible answers"%len(rows))
            maxlencsv   = max(map(len, ['%s.%s'%(row[5], row[2])   for row in rows]))
            maxlennotch = max(map(len, ['[%s.%s]'%(row[6], row[1]) for row in rows]))
            for row in rows:
                fullcsv   = '%s.%s'%(row[5], row[2])
                fullnotch = '[%s.%s]'%(row[6], row[1])
                self.say(sender, " %s %s %s"%(fullcsv.ljust(maxlencsv+2), fullnotch.ljust(maxlennotch+2), row[3]))
                
        elif len(rows) == 1:
            row = rows[0]
            self.say(sender, "=== GET %s %s ==="%(etype.upper(),side.upper()))
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s"%row[2])
            self.say(sender, " $BNotch$N       : %s"%row[1])
            self.say(sender, " $BSearge$N      : %s"%row[0])
            self.say(sender, " $BType/Sig$N    : %s"%row[3])
            #self.say(sender, " $BNotchType$N   : %s"%row[4])            
            self.say(sender, " $BClass$N       : %s"%row[5])            
            self.say(sender, " $BDescription$N : %s"%row[7])
            
        else:
            self.say(sender, "=== GET %s %s ==="%(etype.upper(),side.upper()))
            self.say(sender, " No result for %s"%msg)
            c.close()
            return
            
        c.close()
        dbase.close()
        
    #===================================================================

    #====================== Search commands ============================
    def cmdSearch(self, sender, chan, cmd, msg):
        type_lookup = {'method':'func','field':'field'}
        dbase = sqlite3.connect('database.db')
        c = dbase.cursor()        

        self.say(sender, "=== SEARCH RESULTS ===")
        for side in ['client', 'server']:
                c.execute("""SELECT c.name, c.notch
                            FROM classes c 
                            WHERE (c.name LIKE ?) AND c.side = ?""",
                            ('%%%s%%'%(msg), side))                   
 
                rows = c.fetchall()
                maxlencsv   = max(map(len, [row[0] for row in rows]))
                maxlennotch = max(map(len, [row[1] for row in rows]))
                if len(rows) > 10:
                    self.say(sender, " [%s][ CLASS] Too many results : %d"%(side.upper(),len(rows)))
                else:
                    for row in rows:
                        self.say(sender, " [%s][ CLASS] %s %s"%(side.upper(), row[0].ljust(maxlencsv+2), row[1].ljust(maxlennotch+2)))
               
        for side in ['client', 'server']:
            for etype in ['field', 'method']:
                c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description
                            FROM %ss m LEFT JOIN classes c ON m.class = c.id
                            WHERE (m.decoded LIKE ?) AND m.side = ?"""%
                            etype,
                            ('%%%s%%'%(msg), side))                
                rows = c.fetchall()
                maxlencsv   = max(map(len, ['%s.%s'%(row[5], row[2])   for row in rows]))
                maxlennotch = max(map(len, ['[%s.%s]'%(row[6], row[1]) for row in rows]))
                if len(rows) > 10:
                    self.say(sender, " [%s][%6s] Too many results : %d"%(side.upper(),etype.upper(),len(rows)))
                else:
                    for row in rows:
                        fullcsv   = '%s.%s'%(row[5], row[2])
                        fullnotch = '[%s.%s]'%(row[6], row[1])
                        self.say(sender, " [%s][%s] %s %s %s"%(side.upper(),etype.upper(), fullcsv.ljust(maxlencsv+2), fullnotch.ljust(maxlennotch+2), row[3]))                
                
                
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

