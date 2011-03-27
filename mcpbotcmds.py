import sqlite3
import time
from irc_lib.utils.restricted import restricted
from database import database, getMembers

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

    @database
    def getClass(self, sender, chan, cmd, msg, side, c):
        side_lookup = {'client':0, 'server':1}
        c.execute("""SELECT c1.name, c1.notch, c2.name, c2.notch 
                     FROM classes c1 LEFT JOIN classes c2 ON c1.super = c2.id 
                     WHERE (c1.name = ? OR c1.notch = ?) AND c1.side= ?""",
                     (msg,msg,side_lookup[side]))
        
        rows = c.fetchall()
                
        for row in rows:
            self.say(sender, "=== GET %s CLASS ==="%side.upper())
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s"%row[0])
            self.say(sender, " $BNotch$N       : %s"%row[1])
            self.say(sender, " $BSuper$N       : %s"%row[2])

        if not rows:
            self.say(sender, "=== GET %s CLASS ==="%side.upper())
            self.say(sender, " No result for %s"%msg)
            c.close()
            return

        c.execute("""SELECT m.signature 
                     FROM methods m 
                     INNER JOIN classes c ON m.class = c.id 
                     WHERE (m.name = ? OR m.notch = ?) AND m.side = ? AND m.name = c.name""",(msg,msg,side_lookup[side]))
        for row in c:
            self.say(sender, " $BConstructor$N : %s"%row[0])            

    #===================================================================

    #================== Getters members ================================
    def cmdGcm(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'method')

    def cmdGsm(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'server', 'method')

    def cmdGm(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'method')        
        self.outputMembers(sender, chan, cmd, msg, 'server', 'method')

    def cmdGcf(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'field')

    def cmdGsf(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'server', 'field')

    def cmdGf(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'field')        
        self.outputMembers(sender, chan, cmd, msg, 'server', 'field')

    def outputMembers(self, sender, chan, cmd, msg, side, etype):

        rows = getMembers(msg, side, etype) #m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description

        if len(rows) > 10:
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " $BVERY$N ambiguous request $R'%s'$N"%msg)
            self.say(sender, " Found %s possible answers"%len(rows))        
            self.say(sender, " Not displaying any !")        
        elif 10 >= len(rows) > 1:
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
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
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s.%s"%(row[5],row[2],))
            self.say(sender, " $BNotch$N       : %s.%s"%(row[6],row[1],))
            self.say(sender, " $BSearge$N      : %s"%row[0])
            self.say(sender, " $BType/Sig$N    : %s"%row[3])
            #self.say(sender, " $BNotchType$N   : %s"%row[4])            
            #self.say(sender, " $BClass$N       : %s"%row[5])
            if row[7]:      
                self.say(sender, " $BDescription$N : %s"%row[7])
            
        else:
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " No result for %s"%msg)
            c.close()
            return
        
    #===================================================================

    #====================== Search commands ============================
    @database
    def cmdSearch(self, sender, chan, cmd, msg, c):
        type_lookup = {'method':'func','field':'field'}
        side_lookup = {'client':0, 'server':1}

        self.say(sender, "=== SEARCH RESULTS ===")
        for side in ['client', 'server']:
                c.execute("""SELECT c.name, c.notch
                            FROM classes c 
                            WHERE (c.name LIKE ?) AND c.side = ?""",
                            ('%%%s%%'%(msg), side_lookup[side]))                   
 
                rows = c.fetchall()
                if not rows:
                    self.say(sender, " [%s][ CLASS] No results"%side.upper())
                else:                
                    maxlencsv   = max(map(len, [row[0] for row in rows]))
                    maxlennotch = max(map(len, [row[1] for row in rows]))
                    if len(rows) > 10:
                        self.say(sender, " [%s][ CLASS] Too many results : %d"%(side.upper(),len(rows)))
                    else:
                        for row in rows:
                            self.say(sender, " [%s][ CLASS] %s %s"%(side.upper(), row[0].ljust(maxlencsv+2), row[1].ljust(maxlennotch+2)))
               
        for side in ['client', 'server']:
            for etype in ['field', 'method']:
                c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description, m.id, m.dirty
                            FROM %ss m LEFT JOIN classes c ON m.class = c.id
                            WHERE (m.decoded LIKE ?) AND m.side = ?"""%
                            etype,
                            ('%%%s%%'%(msg), side_lookup[side]))                
                rows = c.fetchall()
               
                if not rows:
                    self.say(sender, " [%s][%6s] No results"%(side.upper(), etype.upper()))
                else:
                    maxlencsv   = max(map(len, ['%s.%s'%(row[5], row[2])   for row in rows]))
                    maxlennotch = max(map(len, ['[%s.%s]'%(row[6], row[1]) for row in rows]))
                    if len(rows) > 10:
                        self.say(sender, " [%s][%6s] Too many results : %d"%(side.upper(),etype.upper(),len(rows)))
                    else:
                        for row in rows:
                            fullcsv   = '%s.%s'%(row[5], row[2])
                            fullnotch = '[%s.%s]'%(row[6], row[1])
                            self.say(sender, " [%s][%6s] %s %s %s"%(side.upper(),etype.upper(), fullcsv.ljust(maxlencsv+2), fullnotch.ljust(maxlennotch+2), row[3]))                
                
    #===================================================================

    #====================== Setters for members ========================
    
    @restricted
    def cmdScm(self, sender, chan, cmd, msg):
        self.setMember(sender, chan, cmd, msg, 'client', 'method')
        
    @restricted
    def cmdScf(self, sender, chan, cmd, msg):
        self.setMember(sender, chan, cmd, msg, 'client', 'field')
        
    @restricted
    def cmdSsm(self, sender, chan, cmd, msg):
        self.setMember(sender, chan, cmd, msg, 'server', 'method')

    @restricted
    def cmdSsf(self, sender, chan, cmd, msg):
        self.setMember(sender, chan, cmd, msg, 'server', 'field')

    @database
    def setMember(self, sender, chan, cmd, msg, side, etype, c):
        
        if len(msg.strip().split()) < 2:
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))            
            self.say(sender, " Not enough parameters : $B%s <oldname> <newname> [description]"%cmd.lower())            
            return
        
        oldname = msg.strip().split()[0]
        newname = msg.strip().split()[1]
        newdesc = None
        if len(msg.strip().split()) > 2:
            newdesc = ' '.join(msg.strip().split()[2:])
        
        rows = getMembers(oldname, side, etype) #m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description

        if len(rows) > 1:
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))            
            self.say(sender, " Ambiguous request $R'%s'$N"%oldname)
            self.say(sender, " Found %s possible answers"%len(rows))
            maxlencsv   = max(map(len, ['%s.%s'%(row[5], row[2])   for row in rows]))
            maxlennotch = max(map(len, ['[%s.%s]'%(row[6], row[1]) for row in rows]))
            for row in rows:
                fullcsv   = '%s.%s'%(row[5], row[2])
                fullnotch = '[%s.%s]'%(row[6], row[1])
                self.say(sender, " %s %s %s"%(fullcsv.ljust(maxlencsv+2), fullnotch.ljust(maxlennotch+2), row[3]))
        elif len(rows) == 0:
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " No result for %s"%oldname)
        else:
            row = rows[0]
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, "$BName$N     : %s => %s"%(row[0], newname))
            self.say(sender, "$BOld desc$N : %s"%(row[7]))
            self.say(sender, "$BNew desc$N : %s"%(newdesc))

            c.execute("""UPDATE %ss SET dirty = ? WHERE id = ?"""%etype, (True, row[8]))
            c.execute("""INSERT INTO %shist VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"""%etype[0],
                        (None, row[8], row[2], row[7], newname, newdesc, time.time(), time.ctime(), sender))

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


#==END OF CLASS==


