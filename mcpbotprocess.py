import csv
import re
import time

from dbconnection import DBConnection


class MCPBotProcess(object):
    def __init__(self, bot, db_name):
        self.bot = bot
        self.db = DBConnection(db_name)
        self.say = self.bot.say

    def get_version(self, c):
        c.execute("""
                SELECT value
                FROM config
                WHERE name='currentversion'
            """)
        result = c.fetchone()
        (idversion,) = result
        return idversion

    def getClass(self, sender, chan, cmd, msg, side, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            side_lookup = {'client': 0, 'server': 1}

            msg_split = msg.strip().split(None, 1)
            if len(msg_split) != 1:
                self.say(sender, " Syntax error: $B%s <classname>$N" % cmd)
                return
            search_class = msg_split[0]

            c.execute("""
                    SELECT name, notch, supername
                    FROM vclasses
                    WHERE (name=? OR notch=?)
                      AND side=? AND versionid=?
                """,
                (search_class, search_class,
                 side_lookup[side], idversion))
            classresults = c.fetchall()

            if not classresults:
                self.say(sender, "$B[ GET %s CLASS ]" % side.upper())
                self.say(sender, " No results found for $B%s" % search_class)
                return

            for classresult in classresults:
                name, notch, supername = classresult

                c.execute("""
                        SELECT sig, notchsig
                        FROM vconstructors
                        WHERE (name=? OR notch=?)
                          AND side=? AND versionid=?
                    """,
                    (search_class, search_class,
                     side_lookup[side], idversion))
                constructorsresult = c.fetchall()

                self.say(sender, "$B[ GET %s CLASS ]" % side.upper())
                self.say(sender, " Side        : $B%s" % side)
                self.say(sender, " Name        : $B%s" % name)
                self.say(sender, " Notch       : $B%s" % notch)
                self.say(sender, " Super       : $B%s" % supername)

                for constructor in constructorsresult:
                    self.say(sender, " Constructor : $B%s$N | $B%s$N" % (constructor[0], constructor[1]))

    def outputMembers(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

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
                c.execute("""
                        SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                        FROM v{etype} m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                          AND (m.classname=? OR m.classnotch=?)
                          AND (m.sig=? OR m.notchsig=?)
                          AND m.side=? AND m.versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname, cname, cname, sname, sname,
                     side_lookup[side], idversion))
                results = c.fetchall()
            elif cname and not sname:
                c.execute("""
                        SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                        FROM v{etype} m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                          AND (m.classname=? OR m.classnotch=?)
                          AND m.side=? AND m.versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname, cname, cname,
                     side_lookup[side], idversion))
                results = c.fetchall()
            elif not cname and sname:
                c.execute("""
                        SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                        FROM v{etype} m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                          AND (m.sig=? OR m.notchsig=?)
                          AND m.side=? AND m.versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname, sname, sname,
                     side_lookup[side], idversion))
                results = c.fetchall()
            else:
                c.execute("""
                        SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                        FROM v{etype} m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                          AND m.side=? AND m.versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname,
                     side_lookup[side], idversion))
                results = c.fetchall()

            if sender in self.bot.dcc.sockets and self.bot.dcc.sockets[sender]:
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
                    fullsearge = '[%s]' % searge
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

    def search(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            side_lookup = {'client': 0, 'server': 1}

            msg_split = msg.strip().split(None, 1)
            if len(msg_split) != 1:
                self.say(sender, " Syntax error: $B%s <name>$N" % cmd)
                return
            search_str = msg_split[0]

            results = {'classes': None, 'fields': None, 'methods': None}

            if sender in self.bot.dcc.sockets and self.bot.dcc.sockets[sender]:
                highlimit = 100
            else:
                highlimit = 10

            self.say(sender, "$B[ SEARCH RESULTS ]")
            for side in ['client', 'server']:
                c.execute("""
                        SELECT c.name, c.notch
                        FROM vclasses c
                        WHERE c.name LIKE ? ESCAPE '!'
                          AND c.side=? AND c.versionid=?
                    """,
                    ('%{0}%'.format(search_str),
                     side_lookup[side], idversion))
                results['classes'] = c.fetchall()

                for etype in ['fields', 'methods']:
                    c.execute("""
                            SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch
                            FROM v{etype} m
                            WHERE m.name LIKE ? ESCAPE '!'
                              AND m.side=? AND m.versionid=?
                        """.format(etype=etype),
                        ('%{0}%'.format(search_str),
                         side_lookup[side], idversion))
                    results[etype] = c.fetchall()

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

    def setMember(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

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
            c.execute("""
                    SELECT m.name
                    FROM vclasses m
                    WHERE lower(m.name)=lower(?)
                      AND m.side=? AND m.versionid=?
                """,
                (newname,
                 side_lookup[side], idversion))
            result = c.fetchone()
            if result:
                self.say(sender, "$RIt is illegal to use class names for fields or methods !")
                return

            ## WE CHECK WE ONLY HAVE ONE RESULT ##
            c.execute("""
                    SELECT m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch, m.id
                    FROM v{etype} m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                      AND m.side=? AND m.versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], oldname), oldname,
                 side_lookup[side], idversion))
            results = c.fetchall()

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
                c.execute("""
                        SELECT m.searge, m.name
                        FROM vmethods m
                        WHERE m.name=?
                          AND m.side=? AND m.versionid=?
                    """,
                    (newname,
                     side_lookup[side], idversion))
                result = c.fetchone()
                if result:
                    self.say(sender, "$RYou are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % result[0])
                    return

                c.execute("""
                        SELECT m.searge, m.name
                        FROM vfields m
                        WHERE m.name=?
                          AND m.side=? AND m.versionid=?
                    """,
                    (newname,
                     side_lookup[side], idversion))
                result = c.fetchone()
                if result:
                    self.say(sender, "$RYou are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % result[0])
                    return

            if not forced:
                c.execute("""
                        SELECT m.searge, m.name
                        FROM vmethods m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                          AND m.side=? AND m.versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], oldname), oldname,
                     side_lookup[side], idversion))
                result = c.fetchone()
                if result and result[0] != result[1]:
                    self.say(sender, "$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                    return

                c.execute("""
                        SELECT m.searge, m.name
                        FROM vfields m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                          AND m.side=? AND m.versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], oldname), oldname,
                     side_lookup[side], idversion))
                result = c.fetchone()
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
                        INSERT INTO {etype}hist
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """.format(etype=etype),
                    (None, int(entryid), name, desc, newname, newdesc, int(time.time()), sender, forced, cmd))
                self.say(sender, "$BNew desc$N : %s" % newdesc)

    def portMember(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

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
            c.execute("""
                    SELECT m.id, m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch, m.id
                    FROM v{etype} m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                      AND m.side=? AND m.versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], origin), origin,
                 side_lookup[side], idversion))
            results = c.fetchall()

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
            c.execute("""
                    SELECT m.id, m.name, m.notch, m.searge, m.sig, m.notchsig, m.desc, m.classname, m.classnotch, m.id
                    FROM v{etype} m
                    WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                      AND m.side=? AND m.versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], target), target,
                 target_side_lookup[side], idversion))
            results_target = c.fetchall()

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
            c.execute("""
                    SELECT m.name
                    FROM vclasses m
                    WHERE lower(m.name)=lower(?)
                      AND m.side=? AND m.versionid=?
                """,
                (origin_name,
                 target_side_lookup[side], idversion))
            result = c.fetchone()
            if result:
                self.say(sender, "$RIt is illegal to use class names for fields or methods !")
                return

            ## WE CHECK THAT WE HAVE A UNIQUE NAME
            if not forced:
                c.execute("""
                        SELECT m.searge, m.name
                        FROM vmethods m
                        WHERE m.name=?
                          AND m.side=? AND m.versionid=?
                    """,
                    (origin_name,
                     target_side_lookup[side], idversion))
                result = c.fetchone()
                if result:
                    self.say(sender, "$RYou are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % result[0])
                    return

                c.execute("""
                        SELECT m.searge, m.name
                        FROM vfields m
                        WHERE m.name=?
                          AND m.side=? AND m.versionid=?
                    """,
                    (origin_name,
                     target_side_lookup[side], idversion))
                result = c.fetchone()
                if result:
                    self.say(sender, "$RYou are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % result[0])
                    return

            if not forced:
                c.execute("""
                        SELECT m.searge, m.name
                        FROM vmethods m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                          AND m.side=? AND m.versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], target), target,
                     side_lookup[side], idversion))
                result = c.fetchone()
                if result and result[0] != result[1]:
                    self.say(sender, "$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                    return

                c.execute("""
                        SELECT m.searge, m.name
                        FROM vfields m
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=?)
                          AND m.side=? AND m.versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], target), target,
                     side_lookup[side], idversion))
                result = c.fetchone()
                if result and result[0] != result[1]:
                    self.say(sender, "$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                    return

            if len(results_target) == 1:
                memberid, name, notch, searge, sig, notchsig, desc, classname, classnotch, entryid = results_target[0]
                self.say(sender, "%s     : $B%s => %s" % (side, origin, target))

                c.execute("""
                        INSERT INTO {etype}hist
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """.format(etype=etype),
                    (None, int(entryid), name, desc, origin_name, origin_desc, int(time.time()), sender, forced, cmd))

    def infoChanges(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            type_lookup = {'methods': 'func', 'fields': 'field'}
            side_lookup = {'client': 0, 'server': 1}

            msg_split = msg.split(None, 1)
            if len(msg_split) != 1:
                self.say(sender, "Syntax error: $B%s <searge|index>" % cmd)
                return
            member = msg_split[0]

            c.execute("""
                        SELECT mh.oldname, mh.olddesc, mh.newname, mh.newdesc,
                          strftime('%m-%d %H:%M', mh.timestamp, 'unixepoch') AS timestamp, mh.nick, mh.forced, m.searge,
                          v.mcpversion
                        FROM {etype} m
                          INNER JOIN versions v ON v.id=m.versionid
                          INNER JOIN {etype}hist mh ON mh.memberid=m.id
                        WHERE (m.searge LIKE ? ESCAPE '!' OR m.searge=? OR m.notch=? OR m.name=?)
                          AND m.side=?
                    """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], member), member, member, member,
                 side_lookup[side]))
            results = c.fetchall()

            if len(results) >= 1:
                for result in results:
                    oldname, olddesc, newname, newdesc, timestamp, nick, forced, searge, version = result
                    self.say(sender, "[%s, %s] %s: %s -> %s" % (version, timestamp, nick, oldname, newname))
            else:
                self.say(sender, "$B[ GET CHANGES %s %s ]" % (side.upper(), etype.upper()))
                self.say(sender, " No result for %s" % msg.strip())

    def revertChanges(self, sender, chan, cmd, msg, side, etype, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            type_lookup = {'methods': 'func', 'fields': 'field'}
            side_lookup = {'client': 0, 'server': 1}

            msg_split = msg.split(None, 1)
            if len(msg_split) != 1:
                self.say(sender, "Syntax error: $B%s <searge|index>" % cmd)
                return
            member = msg_split[0]

            self.say(sender, "$B[ REVERT %s %s ]" % (side.upper(), etype.upper()))

            c.execute("""
                    UPDATE {etype}
                    SET dirtyid=0
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """.format(etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], member), member,
                 side_lookup[side], idversion))
            self.say(sender, " Reverting changes on $B%s$N is done." % member)

    def getlog(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            if self.bot.cnick == 'MCPBot':
                if sender not in self.bot.dcc.sockets or not self.bot.dcc.sockets[sender]:
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
                    c.execute("""
                            SELECT m.name, m.searge, m.desc, h.newname, h.newdesc,
                              strftime('%m-%d %H:%M', h.timestamp, 'unixepoch') AS htimestamp, h.nick, h.cmd, h.forced
                            FROM {etype} m
                              INNER JOIN {etype}hist h ON h.id=m.dirtyid
                            WHERE m.side=? AND m.versionid=?
                            ORDER BY h.timestamp
                        """.format(etype=etype),
                        (side_lookup[side], idversion))
                    results = c.fetchall()

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

    def updateCsv(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            if self.bot.cnick == 'MCPBot':
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

            c.execute("""
                    SELECT classname, searge, name, desc
                    FROM vfields
                    WHERE side=0 AND versionid=?
                    ORDER BY searge
                """,
                (idversion,))
            results = c.fetchall()
            for row in results:
                classname, searge, name, desc = row
                if not desc:
                    desc = ''
                fffield.write('%s,*,%s,*,*,*,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))
            c.execute("""
                    SELECT classname, searge, name, desc
                    FROM vfields
                    WHERE side=1 AND versionid=?
                    ORDER BY searge
                """,
                (idversion,))
            results = c.fetchall()
            for row in results:
                classname, searge, name, desc = row
                if not desc:
                    desc = ''
                fffield.write('*,*,*,%s,*,%s,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))

            c.execute("""
                    SELECT classname, searge, name, desc
                    FROM vmethods
                    WHERE side=0 AND versionid=?
                    ORDER BY searge
                """,
                (idversion,))
            results = c.fetchall()
            for row in results:
                classname, searge, name, desc = row
                if not desc:
                    desc = ''
                ffmetho.write('%s,%s,*,*,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))
            c.execute("""
                    SELECT classname, searge, name, desc
                    FROM vmethods
                    WHERE side=1 AND versionid=?
                    ORDER BY searge
                """,
                (idversion,))
            results = c.fetchall()
            for row in results:
                classname, searge, name, desc = row
                if not desc:
                    desc = ''
                ffmetho.write('*,*,%s,%s,%s,"%s"\n' % (classname, searge, name, desc.replace('"', "'")))

            ffmetho.close()
            fffield.close()

    def dbCommit(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            pushforced = kwargs['pushforced']

            msg_split = msg.strip().split(None, 1)
            if len(msg_split):
                self.say(sender, "Syntax error: $B%s" % cmd)
                return

            nentries = 0
            for etype in ['methods', 'fields']:

                if pushforced:
                    c.execute("""
                            SELECT m.id, h.id, h.newname, h.newdesc
                            FROM {etype} m
                              INNER JOIN {etype}hist h ON h.id=m.dirtyid
                            WHERE m.versionid=?
                        """.format(etype=etype),
                        (idversion,))
                    results = c.fetchall()
                else:
                    c.execute("""
                            SELECT m.id, h.id, h.newname, h.newdesc
                            FROM {etype} m
                              INNER JOIN {etype}hist h ON h.id=m.dirtyid
                            WHERE NOT h.forced=1
                              AND m.versionid=?
                        """.format(etype=etype),
                        (idversion,))
                    results = c.fetchall()
                nentries += len(results)

                for result in results:
                    mid, hid, hnewname, hnewdesc = result
                    c.execute("""
                            UPDATE {etype}
                            SET name=?, desc=?, dirtyid=0
                            WHERE id=?
                        """.format(etype=etype),
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

    def altCsv(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            msg_split = msg.strip().split(None, 1)
            if len(msg_split) > 2:
                self.say(sender, " Syntax error: $B%s [version]$N" % cmd)
                return
            if len(msg_split) == 1:
                version = msg_split[0]
                c.execute("""
                        SELECT id
                        FROM versions
                        WHERE mcpversion=?
                    """,
                    (version,))
                result = c.fetchone()
                if not result:
                    self.say(sender, "Version not recognised.")
                    return
                else:
                    (idversion,) = result

            c.execute("""
                    SELECT mcpversion
                    FROM versions
                    WHERE id=?
                """,
                (idversion,))
            result = c.fetchone()
            (mcpversion,) = result

            if self.bot.cnick == 'MCPBot':
                trgdir = '/home/mcpfiles/mcprolling_%s/mcp/conf' % mcpversion
            else:
                trgdir = 'devconf'

            methodswriter = csv.writer(open('%s/methods.csv' % trgdir, 'wb'))
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vmethods
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            results = c.fetchall()
            methodswriter.writerow(('searge', 'name', 'side', 'desc'))
            for row in results:
                methodswriter.writerow(row)

            fieldswriter = csv.writer(open('%s/fields.csv' % trgdir, 'wb'))
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vfields
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            results = c.fetchall()
            fieldswriter.writerow(('searge', 'name', 'side', 'desc'))
            for row in results:
                fieldswriter.writerow(row)

            self.say(sender, "New CSVs exported")

    def testCsv(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            if self.bot.cnick == 'MCPBot':
                trgdir = '/home/mcpfiles/mcptest'
            else:
                trgdir = 'devconf'

            msg_split = msg.strip().split(None, 1)
            if len(msg_split):
                self.say(sender, "Syntax error: $B%s" % cmd)
                return

            methodswriter = csv.writer(open('%s/methods.csv' % trgdir, 'wb'))
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vmethods
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            results = c.fetchall()
            methodswriter.writerow(('searge', 'name', 'side', 'desc'))
            for row in results:
                methodswriter.writerow(row)

            fieldswriter = csv.writer(open('%s/fields.csv' % trgdir, 'wb'))
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vfields
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            results = c.fetchall()
            fieldswriter.writerow(('searge', 'name', 'side', 'desc'))
            for row in results:
                fieldswriter.writerow(row)

            self.say(sender, "Test CSVs exported: http://mcp.ocean-labs.de/files/mcptest/")

    def status(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            side_lookup = {'client': 0, 'server': 1}

            msg_split = msg.strip().split(None, 1)
            if len(msg_split) > 1:
                self.say(sender, "Syntax error: $B%s [full]" % cmd)
                return
            full_status = False
            if len(msg_split) == 1:
                if msg_split[0] == 'full':
                    full_status = True

            c.execute("""
                    SELECT mcpversion, botversion, dbversion, clientversion, serverversion
                    FROM versions
                    WHERE id=?
                """,
                (idversion,))
            result = c.fetchone()
            mcpversion, botversion, dbversion, clientversion, serverversion = result

            self.say(sender, "$B[ STATUS ]")
            self.say(sender, " MCP    : $B%s" % mcpversion)
            self.say(sender, " Bot    : $B%s" % botversion)
            self.say(sender, " Client : $B%s" % clientversion)
            self.say(sender, " Server : $B%s" % serverversion)

            if full_status:
                for side in ['client', 'server']:
                    for etype in ['methods', 'fields']:
                        c.execute("""
                                SELECT total({etype}t), total({etype}r), total({etype}u)
                                FROM vclassesstats
                                WHERE side=? AND versionid=?
                            """.format(etype=etype),
                            (side_lookup[side], idversion))
                        result = c.fetchone()
                        total, ren, urn = result

                        self.say(sender, " [%s][%7s] : T $B%4d$N | R $B%4d$N | U $B%4d$N | $B%5.2f%%$N" % (side[0].upper(), etype.upper(), total, ren, urn, float(ren) / float(total) * 100))

    def todo(self, sender, chan, cmd, msg, *args, **kwargs):
        with self.db.get_cursor() as c:
            idversion = self.get_version(c)

            side_lookup = {'client': 0, 'server': 1}

            msg_split = msg.strip().split(None, 1)
            if len(msg_split) != 1:
                self.say(sender, "Syntax error: $B%s <client|server>" % cmd)
                return
            search_side = msg_split[0]
            if search_side not in side_lookup:
                self.say(sender, "$Btodo <client|server>")
                return

            c.execute("""
                    SELECT id, name, methodst+fieldst, methodsr+fieldsr, methodsu+fieldsu
                    FROM vclassesstats
                    WHERE side=? AND versionid=?
                    ORDER BY methodsu+fieldsu DESC
                    LIMIT 10
                """,
                (side_lookup[search_side], idversion))
            results = c.fetchall()

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
