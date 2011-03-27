import sqlite3
import time
from irc_lib.utils.restricted import restricted
from database import database

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
        msg = msg.strip()
        c.execute("""SELECT name, notch, supername FROM vclasses WHERE (name = ? OR notch = ?) AND side = ?""", (msg, msg, side_lookup[side]))
        
        classresults = c.fetchall()
        
        if not classresults:
            self.say(sender, "=== GET %s CLASS ==="%side.upper())
            self.say(sender, " No results found for $B%s"%msg)
        
        for classresult in classresults:
            name, notch, supername = classresult

            c.execute("""SELECT sig FROM vconstructors WHERE (name = ? OR notch = ?) AND side = ?""",(msg, msg, side_lookup[side]))
            constructorsresult = c.fetchall()

            self.say(sender, "=== GET %s CLASS ==="%side.upper())
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s"%name)
            self.say(sender, " $BNotch$N       : %s"%notch)
            self.say(sender, " $BSuper$N       : %s"%supername)

            for constructor in constructorsresult:
                self.say(sender, " $BConstructor$N : %s"%constructor[0]) 

    #===================================================================

    #================== Getters members ================================
    def cmdGcm(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'methods')

    def cmdGsm(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmdGm(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'methods')        
        self.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmdGcf(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'fields')

    def cmdGsf(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    def cmdGf(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'fields')        
        self.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    @database
    def outputMembers(self, sender, chan, cmd, msg, side, etype, c):
        side_lookup = {'client':0, 'server':1}
        type_lookup = {'fields':'field', 'methods':'func'}
        msg = msg.strip()
        if   len(msg.split('.')) == 1:
            c.execute("""SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch FROM v%s m
                         WHERE ((m.searge LIKE ? ESCAPE '!') OR m.notch = ? OR m.name = ?) AND m.side = ?"""%etype, 
                         ('%s!_%s!_%%'%(type_lookup[etype],msg),msg,msg,side_lookup[side]))
        elif len(msg.split('.')) == 2:
            cname = msg.split('.')[0]
            mname = msg.split('.')[0]
            c.execute("""SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch FROM v%s m
                         WHERE ((m.searge LIKE ? ESCAPE '!') OR m.notch = ? OR m.name = ?) AND m.side = ? AND (m.classname = ? OR m.classnotch = ?)"""%etype, 
                         ('%s!_%s!_%%'%(type_lookup[etype],msg),mname,mname,side_lookup[side], cname,cname))
        
        results = c.fetchall()

        if len(results) > 10:
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " $BVERY$N ambiguous request $R'%s'$N"%msg)
            self.say(sender, " Found %s possible answers"%len(results))        
            self.say(sender, " Not displaying any !")        
        elif 10 >= len(results) > 1:
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " Ambiguous request $R'%s'$N"%msg)
            self.say(sender, " Found %s possible answers"%len(results))
            maxlencsv   = max(map(len, ['%s.%s'%(result[6], result[0])   for result in results]))
            maxlennotch = max(map(len, ['[%s.%s]'%(result[7], result[1]) for result in results]))
            for result in results:
                name, notch, searge, sig, notchsig, desc, classname, classnotch = result
                fullcsv   = '%s.%s'%(classname, name)
                fullnotch = '[%s.%s]'%(classnotch, notch)
                self.say(sender, " %s %s %s"%(fullcsv.ljust(maxlencsv+2), fullnotch.ljust(maxlennotch+2), sig))
        elif len(results) == 1:
            result = results
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " $BSide$N        : %s"%side)
            self.say(sender, " $BName$N        : %s.%s"%(classname, name,))
            self.say(sender, " $BNotch$N       : %s.%s"%(classnotch, notch,))
            self.say(sender, " $BSearge$N      : %s"%searge)
            self.say(sender, " $BType/Sig$N    : %s"%sig)
            if desc:      
                self.say(sender, " $BDescription$N : %s"%desc)
        else:
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " No result for %s"%msg)
            c.close()
            return
        
    #===================================================================

    #====================== Search commands ============================
    @database
    def cmdSearch(self, sender, chan, cmd, msg, c):
        pass
                
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
        pass

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


