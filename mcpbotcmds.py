import sqlite3
import time
import string
from irc_lib.utils.restricted import restricted
from database import database

class MCPBotCmds(object):
    def cmdDefault(self, sender, chan, cmd, msg):
        print sender, chan, cmd, msg

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

    @restricted        
    def cmdPub(self, sender, chan, cmd, msg):
        cmd = msg.split()[0]
        if len(msg.split()) > 1:
            msg = ' '.join(msg.split()[1:])

        cmd = cmd.lower()
        cmd = cmd[0].upper() + cmd[1:]
        
        if cmd in ['Ssf, Ssm, Scf, Scm']:
            self.say(sender, 'No public setters !')
            return
        
        try:
            getattr(self, 'cmd%s'%cmd )(chan, chan, cmd, msg)
        except AttributeError:
            getattr(self, 'cmdDefault')(chan, chan, cmd, msg)
        
    #===================================================================

    #================== Getters classes ================================
    def cmdGcc(self, sender, chan, cmd, msg):
        """$Bgcc <classname>$N              : Get Client Class."""
        self.getClass(sender, chan, cmd, msg, 'client')

    def cmdGsc(self, sender, chan, cmd, msg):
        """$Bgsc <classname>$N              : Get Server Class."""
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
        """$Bgcm [classname.]<methodname>$N : Get Client Method."""
        self.outputMembers(sender, chan, cmd, msg, 'client', 'methods')

    def cmdGsm(self, sender, chan, cmd, msg):
        """$Bgsm [classname.]<methodname>$N : Get Server Method."""
        self.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmdGm(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'methods')        
        self.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmdGcf(self, sender, chan, cmd, msg):
        """$Bgcf [classname.]<fieldname>$N  : Get Client Field."""
        self.outputMembers(sender, chan, cmd, msg, 'client', 'fields')

    def cmdGsf(self, sender, chan, cmd, msg):
        """$Bgsf [classname.]<fieldname>$N  : Get Server Field."""
        self.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    def cmdGf(self, sender, chan, cmd, msg):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'fields')        
        self.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    @database
    def outputMembers(self, sender, chan, cmd, msg, side, etype, c):
        side_lookup = {'client':0, 'server':1}
        type_lookup = {'fields':'field', 'methods':'func'}
        msg = msg.strip()

        if len(msg.split('.')) > 2 or not msg:
            self.say(sender, "=== GET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " Syntax error. Use $B%s <membername>$N or $B%s <classname>.<membername>$N"%(cmd,cmd))
            return

        elif len(msg.split('.')) == 1:
            c.execute("""SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch FROM v%s m
                         WHERE ((m.searge LIKE ? ESCAPE '!') OR m.searge = ? OR m.notch = ? OR m.name = ?) AND m.side = ?"""%etype, 
                         ('%s!_%s!_%%'%(type_lookup[etype],msg),msg,msg,msg,side_lookup[side]))

        elif len(msg.split('.')) == 2:
            cname = msg.split('.')[0]
            mname = msg.split('.')[1]
            c.execute("""SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch FROM v%s m
                         WHERE ((m.searge LIKE ? ESCAPE '!') OR m.searge = ? OR m.notch = ? OR m.name = ?) AND m.side = ? AND (m.classname = ? OR m.classnotch = ?)"""%etype, 
                         ('%s!_%s!_%%'%(type_lookup[etype],msg),mname,mname,mname,side_lookup[side], cname,cname))
                         
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
            name, notch, searge, sig, notchsig, desc, classname, classnotch = results[0]
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
        """$Bsearch <pattern>$N  : Search for a pattern."""        
        msg.strip()
        type_lookup = {'method':'func','field':'field'}
        side_lookup = {'client':0, 'server':1}

        results = {'classes':None, 'fields':None, 'methods':None}

        self.say(sender, "=== SEARCH RESULTS ===")    
        for side in ['client', 'server']:
            c.execute("""SELECT c.name, c.notch FROM vclasses c WHERE (c.name LIKE ?) AND c.side = ?""",('%%%s%%'%(msg), side_lookup[side]))                   
            results['classes'] = c.fetchall()

            for etype in ['fields', 'methods']:
                c.execute("""SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch FROM v%s m
                            WHERE (m.name LIKE ? ESCAPE '!') AND m.side = ?"""%etype, 
                            ('%%%s%%'%(msg), side_lookup[side]))
                results[etype] = c.fetchall()

            if not results['classes']:
                self.say(sender, " [%s][  CLASS] No results"%side.upper())
            else:                
                maxlenname  = max(map(len, [result[0] for result in results['classes']]))
                maxlennotch = max(map(len, [result[1] for result in results['classes']]))
                if len(results['classes']) > 10:
                    self.say(sender, " [%s][  CLASS] Too many results : %d"%(side.upper(),len(results['classes'])))
                else:
                    for result in results['classes']:
                        name, notch = result
                        self.say(sender, " [%s][  CLASS] %s %s"%(side.upper(), name.ljust(maxlenname+2), notch.ljust(maxlennotch+2)))            


            for etype in ['fields', 'methods']:
                if not results[etype]:
                    self.say(sender, " [%s][%7s] No results"%(side.upper(), etype.upper()))
                else:
                    maxlenname  = max(map(len, ['%s.%s'%(result[6], result[0])   for result in results[etype]]))
                    maxlennotch = max(map(len, ['[%s.%s]'%(result[7], result[1]) for result in results[etype]]))
                    if len(results[etype]) > 10:
                        self.say(sender, " [%s][%7s] Too many results : %d"%(side.upper(),etype.upper(),len(results[etype])))
                    else:
                        for result in results[etype]:
                            name, notch, searge, sig, notchsig, desc, classname, classnotch = result
                            fullname   = '%s.%s'%(classname, name)
                            fullnotch = '[%s.%s]'%(classnotch, notch)
                            self.say(sender, " [%s][%7s] %s %s %s"%(side.upper(),etype.upper(), fullname.ljust(maxlenname+2), fullnotch.ljust(maxlennotch+2), sig))                
                
    #===================================================================

    #====================== Setters for members ========================
    
    def cmdScm(self, sender, chan, cmd, msg):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.setMember(sender, chan, cmd, msg, 'client', 'methods')
        
    def cmdScf(self, sender, chan, cmd, msg):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.setMember(sender, chan, cmd, msg, 'client', 'fields')
        
    def cmdSsm(self, sender, chan, cmd, msg):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.setMember(sender, chan, cmd, msg, 'server', 'methods')

    def cmdSsf(self, sender, chan, cmd, msg):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.setMember(sender, chan, cmd, msg, 'server', 'fields')

    @database
    def setMember(self, sender, chan, cmd, msg, side, etype, c):
        msg = msg.strip()
        type_lookup = {'methods':'func','fields':'field'}
        side_lookup = {'client':0, 'server':1}
        
        if not msg or msg.split() < 2:
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " Syntax error. Use $B%s <membername> <newname> [newdescription]$N"%(cmd))
            return        
        
        msg     = map(string.strip, msg.split())
        oldname = msg[0]
        newname = msg[1]
        newdesc = None
        if len(msg) > 2:
            newdesc = ' '.join(msg[2:])        

        c.execute("""SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch, m.id FROM v%s m
                    WHERE ((m.searge LIKE ? ESCAPE '!') OR m.searge = ?) AND m.side = ?"""%etype, 
                    ('%s!_%s!_%%'%(type_lookup[etype],oldname),oldname,side_lookup[side]))            
        
        results = c.fetchall()

        if len(results) > 1:
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))            
            self.say(sender, " Ambiguous request $R'%s'$N"%oldname)
            self.say(sender, " Found %s possible answers"%len(rows))
            
            maxlencsv   = max(map(len, ['%s.%s'%(result[5], result[2])   for result in results]))
            maxlennotch = max(map(len, ['[%s.%s]'%(result[6], result[1]) for result in results]))
            for result in results:
                name, notch, searge, sig, notchsig, desc, classname, classnotch, id = result
                fullcsv   = '%s.%s'%(classname, name)
                fullnotch = '[%s.%s]'%(classnotch, notch)
                self.say(sender, " %s %s %s"%(fullcsv.ljust(maxlencsv+2), fullnotch.ljust(maxlennotch+2), sig))
                
        elif len(results) == 0:
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, " No result for %s"%oldname)
        else:
            name, notch, searge, sig, notchsig, desc, classname, classnotch, id = results[0]
            self.say(sender, "=== SET %s %s ==="%(side.upper(),etype.upper()))
            self.say(sender, "$BName$N     : %s => %s"%(name, newname))
            self.say(sender, "$BOld desc$N : %s"%(desc))
            self.say(sender, "$BNew desc$N : %s"%(newdesc))

            c.execute("""INSERT INTO %shist VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""%etype,
                (None, int(id), name, desc, newname, newdesc, int(time.time()), sender))

    #===================================================================

    #====================== Log Methods ================================
    @database
    def cmdGetlog(self, sender, chan, cmd, msg, c):
        msg = msg.strip()
        if msg == 'full':fulllog=True
        else: fulllog = False
        
        type_lookup = {'methods':'func','fields':'field'}
        side_lookup = {'client':0, 'server':1}

        self.say(sender, "=== LOGS ===")
        for side  in ['server', 'client']:
            for etype in ['methods', 'fields']:
                c.execute("""SELECT m.name, m.searge, m.desc, h.newname, h.newdesc, strftime('%s',h.timestamp, 'unixepoch') as htimestamp, h.nick
                            FROM  %s m 
                            INNER JOIN %shist h ON m.dirtyid = h.id
                            WHERE m.side = ?"""%('%m-%d %H:%M',etype,etype), (side_lookup[side],))
                    
                results = c.fetchall()
        
                if results:
                    maxlennick   = max(map(len, [result[6] for result in results]))
                    maxlensearge = max(map(len, [result[1] for result in results]))
                    maxlenmname  = max(map(len, [result[0] for result in results]))

                for result in results:
                    mname, msearge, mdesc, hname, hdesc, htimestamp, hnick = result
                    
                    if fulllog:
                        self.say(sender, "+ %s, %s"%(htimestamp, hnick))
                        self.say(sender, "  [%s%s][%s] %s => %s"%(side[0].upper(), etype[0].upper(), msearge.ljust(maxlensearge), mname.ljust(maxlenmname), hname))
                        self.say(sender, "  [%s%s][%s] %s => %s"%(side[0].upper(), etype[0].upper(), msearge.ljust(maxlensearge), mdesc, hdesc))
                    else:
                        self.say(sender, "+ %s, %s [%s%s] %s => %s"%(htimestamp, hnick.ljust(maxlennick), side[0].upper(), etype[0].upper(), msearge.ljust(maxlensearge), hname))

    @restricted
    @database
    def cmdCommit(self, sender, chan, cmd, msg, c):

        nentries = 0
        for etype in ['methods', 'fields']:

            c.execute("""SELECT m.id, h.id, h.newname, h.newdesc FROM %s m
                        INNER JOIN %shist h ON m.dirtyid = h.id
                        """%(etype, etype))
        
            results = c.fetchall()
            nentries += len(results)
            
            for result in results:
                mid, hid, hnewname, hnewdesc = result
                c.execute("""UPDATE %s SET name = ?, desc = ?, dirtyid = 0 WHERE id = ?"""%etype, (hnewname, hnewdesc, mid))  

        if nentries:
            c.execute("""INSERT INTO commits VALUES (?, ?, ?)""",(None, int(time.time()), sender))
            self.say(sender, "=== COMMIT ===")
            self.say(sender, " Committed %d new updates"%nentries)
        else:
            self.say(sender, "=== COMMIT ===")
            self.say(sender, " No new entries to commit")            
    
    #===================================================================

    #====================== Whitelist Handling =========================
    @restricted
    def cmdAddwhite(self, sender, chan, cmd, msg):
        self.addWhitelist(msg)
        
    @restricted
    def cmdRmwhite(self, sender, chan, cmd, msg):
        self.rmWhitelist(msg)
    
    @restricted    
    def cmdGetwhite(self, sender, chan, cmd, msg):
        self.say(sender, "Whitelist : %s"%self.whitelist)
        
    @restricted    
    def cmdSavewhite(self, sender, chan, cmd, msg):
        self.saveWhitelist()
        
    @restricted    
    def cmdLoadwhite(self, sender, chan, cmd, msg):
        self.loadWhitelist()        
    #===================================================================

    #====================== Misc commands ==============================
    @restricted
    def cmdExec(self, sender, chan, cmd, msg):
        if sender != 'ProfMobius': return
        try:
            print msg
            exec(msg) in self.globaldic, self.localdic
        except Exception as errormsg:
            self.printq.put ('ERROR : %s'%errormsg)
            self.say(sender, 'ERROR : %s'%errormsg)

    def cmdDcc(self, sender, chan, cmd, msg):
        """$Bdcc$N : Starts a dcc session. Faster and not under the flood protection."""        
        self.dcc.dcc(sender)        
    
    @restricted
    def cmdKick(self, sender, chan, cmd, msg):
        msg = msg.strip()
        msg = msg.split()
        self.irc.kick(msg[0], msg[1])

    @restricted
    def cmdRawcmd(self, sender, chan, cmd, msg):
        self.irc.rawcmd(msg.strip())

    def cmdHelp(self, sender, chan, cmd, msg):
        self.say(sender, "====== HELP =====")
        members = dir(self)
        for member in members:
            if member[:3] == 'cmd' and getattr(self, member).__doc__:
                self.say(sender, getattr(self, member).__doc__)

#==END OF CLASS==


