import time
import csv
import re
import threading

from irc_lib.utils.restricted import restricted
from irc_lib.utils.ThreadPool import Worker
from database import database


class MCPBotCmds(object):
    def cmdDefault(self, sender, chan, cmd, msg):
        pass

    #================== Base chatting commands =========================
    @restricted(4)
    def cmd_say(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.say(target, outmsg)

    @restricted(4)
    def cmd_msg(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.irc.privmsg(target, outmsg)

    @restricted(4)
    def cmd_notice(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.irc.notice(target, outmsg)

    @restricted(4)
    def cmd_action(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <target> <message>$N" % cmd)
            return
        target = msg_split[0]
        outmsg = msg_split[1]
        self.ctcp.action(target, outmsg)

    @restricted(4)
    def cmd_pub(self, sender, chan, cmd, msg, *args, **kwargs):
        msg = msg.lstrip()
        if not msg:
            return
        if msg[0] == self.controlchar:
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
    def cmd_gcc(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bgcc <classname>$N              : Get Client Class."""
        self.getClass(sender, chan, cmd, msg, 'client')

    def cmd_gsc(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bgsc <classname>$N              : Get Server Class."""
        self.getClass(sender, chan, cmd, msg, 'server')

    def cmd_gc(self, sender, chan, cmd, msg, *args, **kwargs):
        self.getClass(sender, chan, cmd, msg, 'client')
        self.getClass(sender, chan, cmd, msg, 'server')

    @database
    def getClass(self, sender, chan, cmd, msg, side, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        side_lookup = {'client': 0, 'server': 1}

        msg_split = msg.strip().split(None, 1)
        if len(msg_split) != 1:
            self.say(sender, " Syntax error: $B%s <classname>$N" % cmd)
            return
        search_class = msg_split[0]

        classresults = c.execute("""
                SELECT name, notch, supername
                FROM vclasses
                WHERE (name=? OR notch=?)
                  AND side=? AND versionid=?
            """,
            (search_class, search_class,
             side_lookup[side], idversion)).fetchall()

        if not classresults:
            self.say(sender, "$B[ GET %s CLASS ]" % side.upper())
            self.say(sender, " No results found for $B%s" % search_class)
            return

        for classresult in classresults:
            name, notch, supername = classresult

            constructorsresult = c.execute("""
                    SELECT sig, notchsig
                    FROM vconstructors
                    WHERE (name=? OR notch=?)
                      AND side=? AND versionid=?
                """,
                (search_class, search_class,
                 side_lookup[side], idversion)).fetchall()

            self.say(sender, "$B[ GET %s CLASS ]" % side.upper())
            self.say(sender, " Side        : $B%s" % side)
            self.say(sender, " Name        : $B%s" % name)
            self.say(sender, " Notch       : $B%s" % notch)
            self.say(sender, " Super       : $B%s" % supername)

            for constructor in constructorsresult:
                self.say(sender, " Constructor : $B%s$N | $B%s$N" % (constructor[0], constructor[1]))

    #===================================================================

    #================== Getters members ================================
    def cmd_gcm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bgcm [classname.]<methodname>$N : Get Client Method."""
        self.outputMembers(sender, chan, cmd, msg, 'client', 'methods')

    def cmd_gsm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bgsm [classname.]<methodname>$N : Get Server Method."""
        self.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmd_gm(self, sender, chan, cmd, msg, *args, **kwargs):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'methods')
        self.outputMembers(sender, chan, cmd, msg, 'server', 'methods')

    def cmd_gcf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bgcf [classname.]<fieldname>$N  : Get Client Field."""
        self.outputMembers(sender, chan, cmd, msg, 'client', 'fields')

    def cmd_gsf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bgsf [classname.]<fieldname>$N  : Get Server Field."""
        self.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    def cmd_gf(self, sender, chan, cmd, msg, *args, **kwargs):
        self.outputMembers(sender, chan, cmd, msg, 'client', 'fields')
        self.outputMembers(sender, chan, cmd, msg, 'server', 'fields')

    @database
    def outputMembers(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        side_lookup = {'client': 0, 'server': 1}
        type_lookup = {'fields': 'field', 'methods': 'func'}

        msg_split = msg.strip().split(None, 2)
        if len(msg_split) < 1 or len(msg_split) > 2:
            self.say(sender, " Syntax error: $B%s <membername> [signature]$N or $B%s <classname>.<membername> [signature]$N" % (cmd, cmd))
            return
        member = msg_split[0]
        sname = None
        if len(msg_split) > 1:
            sname = msg_split[1]
        cname = None
        mname = None
        split_member = member.split('.', 2)
        if len(split_member) > 2:
            self.say(sender, " Syntax error: $B%s <membername> [signature]$N or $B%s <classname>.<membername> [signature]$N" % (cmd, cmd))
            return
        if len(split_member) > 1:
            cname = split_member[0]
            mname = split_member[1]
        else:
            mname = split_member[0]

        if cname and sname:
            results = c.execute("""
                    SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                    FROM v%s m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                      AND (m.classname=? OR m.classnotch=?)
                      AND (m.sig=? OR m.notchsig=?)
                      AND m.side=? AND m.versionid=?
                """ % etype,
                ('%s!_%s!_%%' % (type_lookup[etype], mname), mname, mname, mname, cname, cname, sname, sname,
                 side_lookup[side], idversion)).fetchall()
        elif cname and not sname:
            results = c.execute("""
                    SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                    FROM v%s m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                      AND (m.classname=? OR m.classnotch=?)
                      AND m.side=? AND m.versionid=?
                """ % etype,
                ('%s!_%s!_%%' % (type_lookup[etype], mname), mname, mname, mname, cname, cname,
                 side_lookup[side], idversion)).fetchall()
        elif not cname and sname:
            results = c.execute("""
                    SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                    FROM v%s m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                      AND (m.sig=? OR m.notchsig=?)
                      AND m.side=? AND m.versionid=?
                """ % etype,
                ('%s!_%s!_%%' % (type_lookup[etype], mname), mname, mname, mname, sname, sname,
                 side_lookup[side], idversion)).fetchall()
        else:
            results = c.execute("""
                    SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                    FROM v%s m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                      AND m.side=? AND m.versionid=?
                """ % etype,
                ('%s!_%s!_%%' % (type_lookup[etype], mname), mname, mname, mname,
                 side_lookup[side], idversion)).fetchall()

        if sender in self.dcc.sockets and self.dcc.sockets[sender]:
            lowlimit = 10
            highlimit = 999
        else:
            lowlimit = 1
            highlimit = 10

        if len(results) > highlimit:
            self.say(sender, "$B[ GET %s %s ]" % (side.upper(), etype.upper()))
            self.say(sender, " $BVERY$N ambiguous request $R'%s'$N" % msg)
            self.say(sender, " Found %s possible answers" % len(results))
            self.say(sender, " Not displaying any !")
        elif highlimit >= len(results) > lowlimit:
            self.say(sender, "$B[ GET %s %s ]" % (side.upper(), etype.upper()))
            self.say(sender, " Ambiguous request $R'%s'$N" % msg)
            self.say(sender, " Found %s possible answers" % len(results))
            maxlencsv = max([len('%s.%s' % (result[6], result[0])) for result in results])
            maxlennotch = max([len('[%s.%s]' % (result[7], result[1])) for result in results])
            for result in results:
                name, notch, searge, sig, notchsig, desc, classname, classnotch = result
                fullcsv = '%s.%s' % (classname, name)
                fullnotch = '[%s.%s]' % (classnotch, notch)
                fullsearge = '[%s]' % (searge)
                self.say(sender, " %s %s %s %s %s" % (fullsearge, fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), sig, notchsig))
        elif lowlimit >= len(results) > 0:
            for result in results:
                name, notch, searge, sig, notchsig, desc, classname, classnotch = result
                self.say(sender, "$B[ GET %s %s ]" % (side.upper(), etype.upper()))
                self.say(sender, " Side        : $B%s" % side)
                self.say(sender, " Name        : $B%s.%s" % (classname, name,))
                self.say(sender, " Notch       : $B%s.%s" % (classnotch, notch,))
                self.say(sender, " Searge      : $B%s" % searge)
                self.say(sender, " Type/Sig    : $B%s$N | $B%s$N" % (sig, notchsig))
                if desc:
                    self.say(sender, " Description : %s" % desc)
        else:
            self.say(sender, "$B[ GET %s %s ]" % (side.upper(), etype.upper()))
            self.say(sender, " No result for %s" % msg.strip())

    #===================================================================

    #====================== Search commands ============================
    @database
    def cmd_search(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bsearch <pattern>$N  : Search for a pattern."""
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        side_lookup = {'client': 0, 'server': 1}

        msg_split = msg.strip().split(None, 1)
        if len(msg_split) != 1:
            self.say(sender, " Syntax error: $B%s <name>$N" % cmd)
            return
        search_str = msg_split[0]

        results = {'classes': None, 'fields': None, 'methods': None}

        if sender in self.dcc.sockets and self.dcc.sockets[sender]:
            highlimit = 100
        else:
            highlimit = 10

        self.say(sender, "$B[ SEARCH RESULTS ]")
        for side in ['client', 'server']:
            results['classes'] = c.execute("""
                    SELECT c.name, c.notch
                    FROM vclasses c
                    WHERE c.name LIKE ? ESCAPE '!'
                      AND c.side=? AND c.versionid=?
                """,
                ('%%%s%%' % search_str,
                 side_lookup[side], idversion)).fetchall()

            for etype in ['fields', 'methods']:
                results[etype] = c.execute("""
                        SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                        FROM v%s m
                        WHERE m.name LIKE ? ESCAPE '!'
                          AND m.side=? AND m.versionid=?
                    """ % etype,
                    ('%%%s%%' % search_str,
                     side_lookup[side], idversion)).fetchall()

            if not results['classes']:
                self.say(sender, " [%s][  CLASS] No results" % side.upper())
            else:
                maxlenname = max([len(result[0]) for result in results['classes']])
                maxlennotch = max([len(result[1]) for result in results['classes']])
                if len(results['classes']) > highlimit:
                    self.say(sender, " [%s][  CLASS] Too many results : %d" % (side.upper(), len(results['classes'])))
                else:
                    for result in results['classes']:
                        name, notch = result
                        self.say(sender, " [%s][  CLASS] %s %s" % (side.upper(), name.ljust(maxlenname + 2), notch.ljust(maxlennotch + 2)))

            for etype in ['fields', 'methods']:
                if not results[etype]:
                    self.say(sender, " [%s][%7s] No results" % (side.upper(), etype.upper()))
                else:
                    maxlenname = max([len('%s.%s' % (result[6], result[0])) for result in results[etype]])
                    maxlennotch = max([len('[%s.%s]' % (result[7], result[1])) for result in results[etype]])
                    if len(results[etype]) > highlimit:
                        self.say(sender, " [%s][%7s] Too many results : %d" % (side.upper(), etype.upper(), len(results[etype])))
                    else:
                        for result in results[etype]:
                            name, notch, searge, sig, notchsig, desc, classname, classnotch = result
                            fullname = '%s.%s' % (classname, name)
                            fullnotch = '[%s.%s]' % (classnotch, notch)
                            self.say(sender, " [%s][%7s] %s %s %s %s" % (side.upper(), etype.upper(), fullname.ljust(maxlenname + 2), fullnotch.ljust(maxlennotch + 2), sig, notchsig))

    #===================================================================

    #====================== Setters for members ========================

    def cmd_scm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.setMember(sender, chan, cmd, msg, 'client', 'methods', forced=False)

    def cmd_scf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.setMember(sender, chan, cmd, msg, 'client', 'fields', forced=False)

    def cmd_ssm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.setMember(sender, chan, cmd, msg, 'server', 'methods', forced=False)

    def cmd_ssf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.setMember(sender, chan, cmd, msg, 'server', 'fields', forced=False)

    def cmd_fscm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.setMember(sender, chan, cmd, msg, 'client', 'methods', forced=True)

    def cmd_fscf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.setMember(sender, chan, cmd, msg, 'client', 'fields', forced=True)

    def cmd_fssm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.setMember(sender, chan, cmd, msg, 'server', 'methods', forced=True)

    def cmd_fssf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.setMember(sender, chan, cmd, msg, 'server', 'fields', forced=True)

    @database
    def setMember(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        forced = kwargs['forced']

        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}

        msg_split = msg.strip().split(None, 2)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <membername> <newname> [newdescription]$N" % cmd)
            return

        oldname = msg_split[0]
        newname = msg_split[1]
        newdesc = None
        if len(msg_split) > 2:
            newdesc = msg_split[2]

        self.say(sender, "$B[ SET %s %s ]" % (side.upper(), etype.upper()))
        if forced:
            self.say(sender, "$RCAREFUL, YOU ARE FORCING AN UPDATE !")

        # DON'T ALLOW STRANGE CHARACTERS IN NAMES
        if re.search(r'[^A-Za-z0-9$_]', newname):
            self.say(sender, "$RIllegal character in name")
            return

        ## WE CHECK IF WE ARE NOT CONFLICTING WITH A CLASS NAME ##
        result = c.execute("""
                SELECT m.name
                FROM vclasses m
                WHERE lower(m.name)=lower(?)
                  AND m.side=? AND m.versionid=?
            """,
            (newname,
             side_lookup[side], idversion)).fetchone()
        if result:
            self.say(sender, "$RIt is illegal to use class names for fields or methods !")
            return

        ## WE CHECK WE ONLY HAVE ONE RESULT ##
        results = c.execute("""
                SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch, m.id
                FROM v%s m
                WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                  AND m.side=? AND m.versionid=?
            """ % etype,
            ('%s!_%s!_%%' % (type_lookup[etype], oldname), oldname,
             side_lookup[side], idversion)).fetchall()

        if len(results) > 1:
            self.say(sender, " Ambiguous request $R'%s'$N" % oldname)
            self.say(sender, " Found %s possible answers" % len(results))

            maxlencsv = max([len('%s.%s' % (result[5], result[2])) for result in results])
            maxlennotch = max([len('[%s.%s]' % (result[6], result[1])) for result in results])
            for result in results:
                name, notch, searge, sig, notchsig, desc, classname, classnotch, methodid = result
                fullcsv = '%s.%s' % (classname, name)
                fullnotch = '[%s.%s]' % (classnotch, notch)
                self.say(sender, " %s %s %s" % (fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), sig))
            return
        elif not len(results):
            self.say(sender, " No result for %s" % oldname)
            return

        ## WE CHECK THAT WE HAVE A UNIQUE NAME
        if not forced:
            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vmethods m
                    WHERE m.name=?
                      AND m.side=? AND m.versionid=?
                """,
                (newname,
                 side_lookup[side], idversion)).fetchone()
            if result:
                self.say(sender, "$RYou are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % result[0])
                return

            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vfields m
                    WHERE m.name=?
                      AND m.side=? AND m.versionid=?
                """,
                (newname,
                 side_lookup[side], idversion)).fetchone()
            if result:
                self.say(sender, "$RYou are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % result[0])
                return

        if not forced:
            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vmethods m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                      AND m.side=? AND m.versionid=?
                """,
                ('%s!_%s!_%%' % (type_lookup[etype], oldname), oldname,
                 side_lookup[side], idversion)).fetchone()
            if result and result[0] != result[1]:
                self.say(sender, "$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                return

            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vfields m
                    WHERE ((m.searge LIKE ? ESCAPE '!') OR m.searge=?)
                      AND m.side=? AND m.versionid=?
                """,
                ('%s!_%s!_%%' % (type_lookup[etype], oldname), oldname,
                 side_lookup[side], idversion)).fetchone()
            if result and result[0] != result[1]:
                self.say(sender, "$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                return

        if len(results) == 1:
            name, notch, searge, sig, notchsig, desc, classname, classnotch, entryid = results[0]
            self.say(sender, "Name     : $B%s => %s" % (name, newname))
            self.say(sender, "$BOld desc$N : %s" % desc)

            if not newdesc and not desc:
                newdesc = None
            elif not newdesc:
                newdesc = desc.replace('"', "'")
            elif newdesc == 'None':
                newdesc = None
            else:
                newdesc = newdesc.replace('"', "'")

            c.execute("""
                    INSERT INTO %shist
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """ % etype,
                (None, int(entryid), name, desc, newname, newdesc, int(time.time()), sender, forced, cmd))
            self.say(sender, "$BNew desc$N : %s" % newdesc)
			
    #===================================================================

    #======================= Port mappings =============================
    @restricted(2)
    def cmd_pcm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.portMember(sender, chan, cmd, msg, 'client', 'methods', forced=False)
    @restricted(2)
    def cmd_pcf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.portMember(sender, chan, cmd, msg, 'client', 'fields', forced=False)
    @restricted(2)
    def cmd_psm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.portMember(sender, chan, cmd, msg, 'server', 'methods', forced=False)
    @restricted(2)
    def cmd_psf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.portMember(sender, chan, cmd, msg, 'server', 'fields', forced=False)
    @restricted(2)
    def cmd_fpcm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscm [<id>|<searge>] <newname> [description]$N : Set Client Method."""
        self.portMember(sender, chan, cmd, msg, 'client', 'methods', forced=True)
    @restricted(2)
    def cmd_fpcf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bscf [<id>|<searge>] <newname> [description]$N : Set Server Method."""
        self.portMember(sender, chan, cmd, msg, 'client', 'fields', forced=True)
    @restricted(2)
    def cmd_fpsm(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssm [<id>|<searge>] <newname> [description]$N : Set Client Field."""
        self.portMember(sender, chan, cmd, msg, 'server', 'methods', forced=True)
    @restricted(2)
    def cmd_fpsf(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bssf [<id>|<searge>] <newname> [description]$N : Set Server Field."""
        self.portMember(sender, chan, cmd, msg, 'server', 'fields', forced=True)

    @database
    def portMember(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        forced = kwargs['forced']

        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}
        target_side_lookup = {'client': 1, 'server': 0}

        msg_split = msg.strip().split(None, 2)
        if len(msg_split) < 2:
            self.say(sender, " Syntax error: $B%s <origin_member> <target_member>$N" % cmd)
            return

        origin = msg_split[0]
        target = msg_split[1]

        self.say(sender, "$B[ PORT %s %s ]" % (side.upper(), etype.upper()))
        if forced:
            self.say(sender, "$RCAREFUL, YOU ARE FORCING AN UPDATE !")

        ## WE CHECK WE ONLY HAVE ONE RESULT ##
        results = c.execute("""
                SELECT m.id, m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch, m.id
                FROM v%s m
                WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                  AND m.side=? AND m.versionid=?
            """ % etype,
            ('%s!_%s!_%%' % (type_lookup[etype], origin), origin,
             side_lookup[side], idversion)).fetchall()

        if len(results) > 1:
            self.say(sender, " Ambiguous request $R'%s'$N" % origin)
            self.say(sender, " Found %s possible answers" % len(results))

            maxlencsv = max([len('%s.%s' % (result[5], result[2])) for result in results])
            maxlennotch = max([len('[%s.%s]' % (result[6], result[1])) for result in results])
            for result in results:
                name, notch, searge, sig, notchsig, desc, classname, classnotch, methodid = result
                fullcsv = '%s.%s' % (classname, name)
                fullnotch = '[%s.%s]' % (classnotch, notch)
                self.say(sender, " %s %s %s" % (fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), sig))
            return
        elif not len(results):
            self.say(sender, " No result for %s" % origin)
            return
		
        origin_id, origin_name, origin_notch, origin_searge, origin_sig, origin_notchsig, origin_desc, origin_classname, origin_classnotch, origin_methodid = results[0]
		
		# DO THE SAME FOR OTHER SIDE #
        results_target = c.execute("""
                SELECT m.id, m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch, m.id
                FROM v%s m
                WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                  AND m.side=? AND m.versionid=?
            """ % etype,
            ('%s!_%s!_%%' % (type_lookup[etype], target), target,
             target_side_lookup[side], idversion)).fetchall()

        if len(results_target) > 1:
            self.say(sender, " Ambiguous request $R'%s'$N" % target)
            self.say(sender, " Found %s possible answers" % len(results_target))

            maxlencsv = max([len('%s.%s' % (result[5], result[2])) for result in results_target])
            maxlennotch = max([len('[%s.%s]' % (result[6], result[1])) for result in results_target])
            for result in results_target:
                name, notch, searge, sig, notchsig, desc, classname, classnotch, methodid = result
                fullcsv = '%s.%s' % (classname, name)
                fullnotch = '[%s.%s]' % (classnotch, notch)
                self.say(sender, " %s %s %s" % (fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), sig))
            return
        elif not len(results_target):
            self.say(sender, " No result for %s" % target)
            return
		
        target_id, target_name, target_notch, target_searge, target_sig, target_notchsig, target_desc, target_classname, target_classnotch, target_methodid = results_target[0]
		
        ## WE CHECK IF WE ARE NOT CONFLICTING WITH A CLASS NAME ##
        result = c.execute("""
                SELECT m.name
                FROM vclasses m
                WHERE lower(m.name)=lower(?)
                  AND m.side=? AND m.versionid=?
            """,
            (origin_name,
             target_side_lookup[side], idversion)).fetchone()
        if result:
            self.say(sender, "$RIt is illegal to use class names for fields or methods !")
            return

        ## WE CHECK THAT WE HAVE A UNIQUE NAME
        if not forced:
            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vmethods m
                    WHERE m.name=?
                      AND m.side=? AND m.versionid=?
                """,
                (origin_name,
                 target_side_lookup[side], idversion)).fetchone()
            if result:
                self.say(sender, "$RYou are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % result[0])
                return

            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vfields m
                    WHERE m.name=?
                      AND m.side=? AND m.versionid=?
                """,
                (origin_name,
                 target_side_lookup[side], idversion)).fetchone()
            if result:
                self.say(sender, "$RYou are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % result[0])
                return

        if not forced:
            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vmethods m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                      AND m.side=? AND m.versionid=?
                """,
                ('%s!_%s!_%%' % (type_lookup[etype], target), target,
                 side_lookup[side], idversion)).fetchone()
            if result and result[0] != result[1]:
                self.say(sender, "$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                return

            result = c.execute("""
                    SELECT m.searge, m.name
                    FROM vfields m
                    WHERE ((m.searge LIKE ? ESCAPE '!') OR m.searge=?)
                      AND m.side=? AND m.versionid=?
                """,
                ('%s!_%s!_%%' % (type_lookup[etype], target), target,
                 side_lookup[side], idversion)).fetchone()
            if result and result[0] != result[1]:
                self.say(sender, "$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                return

        if len(results_target) == 1:
            id, name, notch, searge, sig, notchsig, desc, classname, classnotch, entryid = results_target[0]
            self.say(sender, "%s     : $B%s => %s" % (side, origin, target))

            c.execute("""
                    INSERT INTO %shist
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """ % etype,
                (None, int(entryid), name, desc, origin_name, origin_desc, int(time.time()), sender, forced, cmd))
			
    #===================================================================

    #======================= Mapping info ==============================
	
    @restricted(2)
    def cmd_icm(self, sender, chan, cmd, msg, *args, **kwargs):
        self.infoChanges(sender, chan, cmd, msg, 'client', 'methods')
		
    @restricted(2)
    def cmd_icf(self, sender, chan, cmd, msg, *args, **kwargs):
        self.infoChanges(sender, chan, cmd, msg, 'client', 'fields')

    @restricted(2)
    def cmd_ism(self, sender, chan, cmd, msg, *args, **kwargs):
        self.infoChanges(sender, chan, cmd, msg, 'server', 'methods')

    @restricted(2)
    def cmd_isf(self, sender, chan, cmd, msg, *args, **kwargs):
        self.infoChanges(sender, chan, cmd, msg, 'server', 'fields')

    @database
    def infoChanges(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}
		
        msg_split = msg.split(None, 1)
        if len(msg_split) != 1:
            self.say(sender, "Syntax error: $B%s <searge|index>" % cmd)
            return
        member = msg_split[0]
			
        results = c.execute("""
                    SELECT mh.oldname, mh.olddesc, mh.newname, mh.newdesc, strftime('%s', mh.timestamp, 'unixepoch') AS timestamp, mh.nick, mh.forced, m.searge, v.mcpversion
					FROM %shist mh, %s m, versions v
					WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
						AND mh.memberid = m.id
						AND m.side = ?
						AND v.id = m.versionid
                """ % ('%m-%d %H:%M', etype, etype),
                ('%s!_%s!_%%' % (type_lookup[etype], member), member, member, member,
                 side_lookup[side])).fetchall()
				 
        if len(results) >= 1:
            for result in results:
                oldname, olddesc, newname, newdesc, timestamp, nick, forced, searge, version = result
                self.say(sender, "[%s, %s] %s: %s -> %s" % (version, timestamp, nick, oldname, newname))
        else:
            self.say(sender, "$B[ GET CHANGES %s %s ]" % (side.upper(), etype.upper()))
            self.say(sender, " No result for %s" % msg.strip())
		

    #===================================================================

    #====================== Revert changes =============================

    @restricted(2)
    def cmd_rcm(self, sender, chan, cmd, msg, *args, **kwargs):
        self.revertChanges(sender, chan, cmd, msg, 'client', 'methods')

    @restricted(2)
    def cmd_rcf(self, sender, chan, cmd, msg, *args, **kwargs):
        self.revertChanges(sender, chan, cmd, msg, 'client', 'fields')

    @restricted(2)
    def cmd_rsm(self, sender, chan, cmd, msg, *args, **kwargs):
        self.revertChanges(sender, chan, cmd, msg, 'server', 'methods')

    @restricted(2)
    def cmd_rsf(self, sender, chan, cmd, msg, *args, **kwargs):
        self.revertChanges(sender, chan, cmd, msg, 'server', 'fields')

    @database
    def revertChanges(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}

        msg_split = msg.split(None, 1)
        if len(msg_split) != 1:
            self.say(sender, "Syntax error: $B%s <searge|index>" % cmd)
            return
        member = msg_split[0]

        self.say(sender, "$B[ REVERT %s %s ]" % (side.upper(), etype.upper()))

        c.execute("""
                UPDATE %s
                SET dirtyid=0
                WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                  AND side=? AND versionid=?
            """ % etype,
            ('%s!_%s!_%%' % (type_lookup[etype], member), member,
             side_lookup[side], idversion))
        self.say(sender, " Reverting changes on $B%s$N is done." % member)

    #===================================================================

    #====================== Log Methods ================================
    @database
    def cmd_getlog(self, sender, chan, cmd, msg, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        if self.cnick == 'MCPBot':
            if sender not in self.dcc.sockets or not self.dcc.sockets[sender]:
                self.say(sender, "$BPlease use DCC for getlog")
                return

        msg_split = msg.strip().split(None, 1)
        if len(msg_split) > 1:
            self.say(sender, "Syntax error: $B%s [full]" % cmd)
            return
        fulllog = False
        if len(msg_split) == 1:
            if msg_split[0] == 'full':
                fulllog = True

        side_lookup = {'client': 0, 'server': 1}

        self.say(sender, "$B[ LOGS ]")
        for side in ['server', 'client']:
            for etype in ['methods', 'fields']:
                results = c.execute("""
                        SELECT m.name, m.searge, m.desc, h.newname, h.newdesc,
                          strftime('%s', h.timestamp, 'unixepoch') AS htimestamp, h.nick, h.cmd, h.forced
                        FROM %s m
                          INNER JOIN %shist h ON h.id=m.dirtyid
                        WHERE m.side=? AND m.versionid=?
                        ORDER BY h.timestamp
                    """ % ('%m-%d %H:%M', etype, etype),
                    (side_lookup[side], idversion)).fetchall()

                if results:
                    maxlennick = max([len(result[6]) for result in results])
                    maxlensearge = max([len(result[1]) for result in results])
                    maxlenmname = max([len(result[0]) for result in results])

                    for forcedstatus in [0, 1]:
                        for result in results:
                            mname, msearge, mdesc, hname, hdesc, htimestamp, hnick, hcmd, hforced = result

                            if hforced == forcedstatus:
                                if fulllog:
                                    self.say(sender, "+ %s, %s, %s" % (htimestamp, hnick, hcmd))
                                    self.say(sender, "  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), msearge.ljust(maxlensearge), mname.ljust(maxlenmname), hname))
                                    self.say(sender, "  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), msearge.ljust(maxlensearge), mdesc, hdesc))
                                else:
                                    indexmember = re.search('[0-9]+', msearge).group()
                                    self.say(sender, "+ %s, %s [%s%s][%5s][%4s] %s => %s" % (htimestamp, hnick.ljust(maxlennick), side[0].upper(), etype[0].upper(), indexmember, hcmd, mname.ljust(maxlensearge), hname))

    @restricted(3)
    def cmd_commit(self, sender, chan, cmd, msg, *args, **kwargs):
        self.dbCommit(sender, chan, cmd, msg, pushforced=False)

    @restricted(4)
    def cmd_fcommit(self, sender, chan, cmd, msg, *args, **kwargs):
        self.dbCommit(sender, chan, cmd, msg, pushforced=True)

    @restricted(3)
    def cmd_updatecsv(self, sender, chan, cmd, msg, *args, **kwargs):
        self.dbCommit(sender, chan, cmd, msg, pushforced=False)
        self.updateCsv(sender, chan, cmd, msg)

    @restricted(4)
    def cmd_fupdatecsv(self, sender, chan, cmd, msg, *args, **kwargs):
        self.dbCommit(sender, chan, cmd, msg, pushforced=True)
        self.updateCsv(sender, chan, cmd, msg)

    @database
    def updateCsv(self, sender, chan, cmd, msg, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        if self.cnick == 'MCPBot':
            directory = '/home/mcpfiles/renamer_csv'
        else:
            directory = 'devconf'

        outfieldcsv = 'fields.csv'
        outmethodcsv = 'methods.csv'

        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return

        ffmetho = open('%s/%s' % (directory, outmethodcsv), 'w')
        fffield = open('%s/%s' % (directory, outfieldcsv), 'w')

        for i in range(2):
            ffmetho.write('NULL,NULL,NULL,NULL,NULL,NULL\n')
            fffield.write('NULL,NULL,NULL,NULL,NULL,NULL\n')
        fffield.write('Class,Field,Name,Class,Field,Name,Name,Notes\n')
        ffmetho.write('NULL,NULL,NULL,NULL,NULL,NULL\n')
        ffmetho.write('class (for reference only),Reference,class (for reference only),Reference,Name,Notes\n')

        results = c.execute("""
                SELECT classname, searge, name, desc
                FROM vfields
                WHERE side=0 AND versionid=?
                ORDER BY searge
            """,
            (idversion,)).fetchall()
        for row in results:
            classname, searge, name, desc = row
            if not desc:
                desc = ''
            fffield.write('%s,*,%s,*,*,*,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))
        results = c.execute("""
                SELECT classname, searge, name, desc
                FROM vfields
                WHERE side=1 AND versionid=?
                ORDER BY searge
            """,
            (idversion,)).fetchall()
        for row in results:
            classname, searge, name, desc = row
            if not desc:
                desc = ''
            fffield.write('*,*,*,%s,*,%s,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))

        results = c.execute("""
                SELECT classname, searge, name, desc
                FROM vmethods
                WHERE side=0 AND versionid=?
                ORDER BY searge
            """,
            (idversion,)).fetchall()
        for row in results:
            classname, searge, name, desc = row
            if not desc:
                desc = ''
            ffmetho.write('%s,%s,*,*,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))
        results = c.execute("""
                SELECT classname, searge, name, desc
                FROM vmethods
                WHERE side=1 AND versionid=?
                ORDER BY searge
            """,
            (idversion,)).fetchall()
        for row in results:
            classname, searge, name, desc = row
            if not desc:
                desc = ''
            ffmetho.write('*,*,%s,%s,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))

        ffmetho.close()
        fffield.close()

    @restricted(3)
    @database
    def cmd_altcsv(self, sender, chan, cmd, msg, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        if self.cnick == 'MCPBot':
            trgdir = '/home/mcpfiles/mcprolling_6.1/mcp/conf'
        else:
            trgdir = 'devconf'

        msg_split = msg.strip().split(None, 1)
        if len(msg_split) > 2:
            self.say(sender, " Syntax error: $B%s [version]$N" % cmd)
            return
        if len(msg_split) == 1:
            version = msg_split[0]
            result = c.execute("""
                    SELECT id
                    FROM versions
                    WHERE mcpversion=?
                """,
                (version,)).fetchone()
            if not result:
                self.say(sender, "Version not recognised.")
                return
            else:
                (idversion,) = result

        result = c.execute("""
                SELECT mcpversion
                FROM versions
                WHERE id=?
            """,
            (idversion,)).fetchone()
        (mcpversion,) = result

        methodswriter = csv.writer(open('%s/methods.csv' % trgdir, 'wb'))
        results = c.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vmethods
                WHERE name != classname
                  AND searge != name
                  AND versionid=?
                ORDER BY side, searge
            """,
            (idversion,)).fetchall()
        methodswriter.writerow(('searge', 'name', 'side', 'desc'))
        for row in results:
            methodswriter.writerow(row)

        fieldswriter = csv.writer(open('%s/fields.csv' % trgdir, 'wb'))
        results = c.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vfields
                WHERE name != classname
                  AND searge != name
                  AND versionid=?
                ORDER BY side, searge
            """,
            (idversion,)).fetchall()
        fieldswriter.writerow(('searge', 'name', 'side', 'desc'))
        for row in results:
            fieldswriter.writerow(row)

        self.say(sender, "New CSVs exported")

    @restricted(2)
    @database
    def cmd_testcsv(self, sender, chan, cmd, msg, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        if self.cnick == 'MCPBot':
            trgdir = '/home/mcpfiles/mcptest'
        else:
            trgdir = 'devconf'

        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return

        methodswriter = csv.writer(open('%s/methods.csv' % trgdir, 'wb'))
        results = c.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vmethods
                WHERE name != classname
                  AND searge != name
                  AND versionid=?
                ORDER BY side, searge
            """,
            (idversion,)).fetchall()
        methodswriter.writerow(('searge', 'name', 'side', 'desc'))
        for row in results:
            methodswriter.writerow(row)

        fieldswriter = csv.writer(open('%s/fields.csv' % trgdir, 'wb'))
        results = c.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vfields
                WHERE name != classname
                  AND searge != name
                  AND versionid=?
                ORDER BY side, searge
            """,
            (idversion,)).fetchall()
        fieldswriter.writerow(('searge', 'name', 'side', 'desc'))
        for row in results:
            fieldswriter.writerow(row)

        self.say(sender, "Test CSVs exported: http://mcp.ocean-labs.de/files/mcptest/")

    @database
    def dbCommit(self, sender, chan, cmd, msg, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        pushforced = kwargs['pushforced']

        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return

        nentries = 0
        for etype in ['methods', 'fields']:

            if pushforced:
                results = c.execute("""
                        SELECT m.id, h.id, h.newname, h.newdesc
                        FROM %s m
                          INNER JOIN %shist h ON h.id=m.dirtyid
                        WHERE m.versionid=?
                    """ % (etype, etype),
                    (idversion,)).fetchall()
            else:
                results = c.execute("""
                        SELECT m.id, h.id, h.newname, h.newdesc
                        FROM %s m
                          INNER JOIN %shist h ON h.id=m.dirtyid
                        WHERE NOT h.forced=1
                          AND m.versionid=?
                    """ % (etype, etype),
                    (idversion,)).fetchall()
            nentries += len(results)

            for result in results:
                mid, hid, hnewname, hnewdesc = result
                c.execute("""
                        UPDATE %s
                        SET name=?, desc=?, dirtyid=0
                        WHERE id=?
                    """ % etype,
                    (hnewname, hnewdesc, mid))

        if nentries:
            c.execute("""
                    INSERT INTO commits
                    VALUES (?, ?, ?)
                """,
                (None, int(time.time()), sender))
            self.say(sender, "$B[ COMMIT ]")
            self.say(sender, " Committed %d new updates" % nentries)
        else:
            self.say(sender, "$B[ COMMIT ]")
            self.say(sender, " No new entries to commit")

    #===================================================================

    #====================== Whitelist Handling =========================
    @restricted(0)
    def cmd_addwhite(self, sender, chan, cmd, msg, *args, **kwargs):
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
        if level >= self.whitelist[sender]:
            self.say(sender, "You don't have the rights to do that.")
            return
        self.addWhitelist(nick, level)
        self.say(sender, "Added %s with level %d to whitelist" % (nick, level))

    @restricted(0)
    def cmd_rmwhite(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split) != 1:
            self.say(sender, "Syntax error: $B%s <nick>" % cmd)
            return
        nick = msg_split[0]

        if nick in self.whitelist and self.whitelist[nick] >= self.whitelist[sender]:
            self.say(sender, "You don't have the rights to do that.")
            return

        try:
            self.rmWhitelist(nick)
        except KeyError:
            self.say(sender, "User %s not found in the whitelist" % nick)
            return
        self.say(sender, "User %s removed from the whitelist" % nick)

    @restricted(0)
    def cmd_getwhite(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.say(sender, "Whitelist : %s" % self.whitelist)

    @restricted(4)
    def cmd_savewhite(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.saveWhitelist()

    @restricted(4)
    def cmd_loadwhite(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.loadWhitelist()
    #===================================================================

    #====================== Misc commands ==============================
    def cmd_dcc(self, sender, chan, cmd, msg, *args, **kwargs):
        """$Bdcc$N : Starts a dcc session. Faster and not under the flood protection."""
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return
        self.dcc.dcc(sender)

    @restricted(4)
    def cmd_kick(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 2)
        if len(msg_split) < 2:
            self.say(sender, "Syntax error: $B%s <channel> <target> [message]" % cmd)
            return
        if len(msg_split) > 2:
            self.irc.kick(msg_split[0], msg_split[1], msg_split[2])
        else:
            self.irc.kick(msg_split[0], msg_split[1])

    @restricted(5)
    def cmd_rawcmd(self, sender, chan, cmd, msg, *args, **kwargs):
        self.irc.rawcmd(msg)

    def cmd_help(self, sender, chan, cmd, msg, *args, **kwargs):
        self.say(sender, "$B[ HELP ]")
        self.say(sender, "For help, please check : http://mcp.ocean-labs.de/index.php/MCPBot")

    @database
    def cmd_status(self, sender, chan, cmd, msg, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        side_lookup = {'client': 0, 'server': 1}

        msg_split = msg.strip().split(None, 1)
        if len(msg_split) > 1:
            self.say(sender, "Syntax error: $B%s [full]" % cmd)
            return
        full_status = False
        if len(msg_split) == 1:
            if msg_split[0] == 'full':
                full_status = True

        result = c.execute("""
                SELECT mcpversion, botversion, dbversion, clientversion, serverversion
                FROM versions
                WHERE id=?
            """,
            (idversion,)).fetchone()
        mcpversion, botversion, dbversion, clientversion, serverversion = result

        self.say(sender, "$B[ STATUS ]")
        self.say(sender, " MCP    : $B%s" % mcpversion)
        self.say(sender, " Bot    : $B%s" % botversion)
        self.say(sender, " Client : $B%s" % clientversion)
        self.say(sender, " Server : $B%s" % serverversion)

        if full_status:
            for side in ['client', 'server']:
                for etype in ['methods', 'fields']:
                    result = c.execute("""
                            SELECT total(%st), total(%sr), total(%su)
                            FROM vclassesstats
                            WHERE side=? AND versionid=?
                        """ % (etype, etype, etype),
                        (side_lookup[side], idversion)).fetchone()
                    total, ren, urn = result

                    self.say(sender, " [%s][%7s] : T $B%4d$N | R $B%4d$N | U $B%4d$N | $B%5.2f%%$N" % (side[0].upper(), etype.upper(), total, ren, urn, float(ren) / float(total) * 100))

        nthreads = len(threading.enumerate())
        if nthreads == self.nthreads + 1:
            self.say(sender, " All threads up and running !")
        else:
            self.say(sender, " Found only $R%d$N threads ! $BThere is a problem !" % (nthreads - 1))

    @restricted(4)
    def cmd_listthreads(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return

        threads = threading.enumerate()
        self.say(sender, "$B[ THREADS ]")
        maxthreadname = max([len(i.name) for i in threads])

        for t in threads:
            if isinstance(t, Worker):
                line = '%s %4d %4d %4d' % (t.name.ljust(maxthreadname), t.ncalls, t.nscalls, t.nfcalls)
            else:
                line = '%s %4d %4d %4d' % (t.name.ljust(maxthreadname), 0, 0, 0)
            self.say(sender, line)

    @restricted(4)
    def cmd_listdcc(self, sender, chan, cmd, msg, *args, **kwargs):
        msg_split = msg.strip().split(None, 1)
        if len(msg_split):
            self.say(sender, "Syntax error: $B%s" % cmd)
            return

        self.say(sender, str(self.dcc.sockets.keys()))

    @database
    def cmd_todo(self, sender, chan, cmd, msg, *args, **kwargs):
        c = kwargs['cursor']
        idversion = kwargs['idvers']

        side_lookup = {'client': 0, 'server': 1}

        msg_split = msg.strip().split(None, 1)
        if len(msg_split) != 1:
            self.say(sender, "Syntax error: $B%s <client|server>" % cmd)
            return
        search_side = msg_split[0]
        if search_side not in side_lookup:
            self.say(sender, "$Btodo <client|server>")
            return

        results = c.execute("""
                SELECT id, name, methodst+fieldst, methodsr+fieldsr, methodsu+fieldsu
                FROM vclassesstats
                WHERE side=? AND versionid=?
                ORDER BY methodsu+fieldsu DESC
                LIMIT 10
            """,
            (side_lookup[search_side], idversion)).fetchall()

        self.say(sender, "$B[ TODO %s ]" % search_side.upper())
        for result in results:
            classid, name, memberst, membersr, membersu = result
            if not memberst:
                memberst = 0
            if not membersr:
                membersr = 0
            if not membersu:
                membersu = 0
            if not membersr:
                percent = 0.
            else:
                percent = float(membersr) / float(memberst) * 100.0
            self.say(sender, " %s : $B%2d$N [ T $B%3d$N | R $B%3d$N | $B%5.2f%%$N ] " % (name.ljust(20), membersu, memberst, membersr, percent))
