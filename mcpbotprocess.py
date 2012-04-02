import csv
import re
import time


class MCPBotProcess(object):
    def __init__(self, cmds):
        self.commands = cmds
        self.ev = self.commands.ev
        self.reply = self.commands.reply
        self.bot = self.commands.bot
        self.db = self.bot.db

    @staticmethod
    def get_version(c):
        c.execute("""
                SELECT value
                FROM config
                WHERE name='currentversion'
            """)
        row = c.fetchone()
        idversion = row['value']
        return idversion

    def getClass(self, side):
        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            side_lookup = {'client': 0, 'server': 1}

            msg_split = self.ev.msg.strip().split(None, 1)
            if len(msg_split) != 1:
                self.reply(" Syntax error: $B%s <classname>$N" % self.ev.cmd)
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
            class_rows = c.fetchall()

            if not class_rows:
                self.reply("$B[ GET %s CLASS ]" % side.upper())
                self.reply(" No results found for $B%s" % search_class)
                return

            for class_row in class_rows:
                self.reply("$B[ GET %s CLASS ]" % side.upper())
                self.reply(" Side        : $B%s" % side)
                self.reply(" Name        : $B%s" % class_row['name'])
                self.reply(" Notch       : $B%s" % class_row['notch'])
                self.reply(" Super       : $B%s" % class_row['supername'])

                c.execute("""
                        SELECT sig, notchsig
                        FROM vconstructors
                        WHERE (name=? OR notch=?)
                          AND side=? AND versionid=?
                    """,
                    (search_class, search_class,
                     side_lookup[side], idversion))
                const_rows = c.fetchall()

                for const_row in const_rows:
                    self.reply(" Constructor : $B%s$N | $B%s$N" % (const_row['sig'], const_row['notchsig']))

    def outputMembers(self, side, etype):
        side_lookup = {'client': 0, 'server': 1}
        type_lookup = {'fields': 'field', 'methods': 'func'}

        msg_split = self.ev.msg.strip().split(None, 2)
        if len(msg_split) < 1 or len(msg_split) > 2:
            self.reply(" Syntax error: $B%s <membername> [signature]$N or $B%s <classname>.<membername> [signature]$N" % (self.ev.cmd, self.ev.cmd))
            return
        member = msg_split[0]
        sname = None
        if len(msg_split) > 1:
            sname = msg_split[1]
        split_member = member.split('.', 2)
        if len(split_member) > 2:
            self.reply(" Syntax error: $B%s <membername> [signature]$N or $B%s <classname>.<membername> [signature]$N" % (self.ev.cmd, self.ev.cmd))
            return
        if len(split_member) > 1:
            cname = split_member[0]
            mname = split_member[1]
        else:
            cname = None
            mname = split_member[0]

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ GET %s %s ]" % (side.upper(), etype.upper()))

            if cname and sname:
                c.execute("""
                        SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                        FROM v{etype}
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                          AND (classname=? OR classnotch=?)
                          AND (sig=? OR notchsig=?)
                          AND side=? AND versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname, cname, cname, sname, sname,
                     side_lookup[side], idversion))
            elif cname and not sname:
                c.execute("""
                        SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                        FROM v{etype}
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                          AND (classname=? OR classnotch=?)
                          AND side=? AND versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname, cname, cname,
                     side_lookup[side], idversion))
            elif not cname and sname:
                c.execute("""
                        SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                        FROM v{etype}
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                          AND (sig=? OR notchsig=?)
                          AND side=? AND versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname, sname, sname,
                     side_lookup[side], idversion))
            else:
                c.execute("""
                        SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                        FROM v{etype}
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                          AND side=? AND versionid=?
                    """.format(etype=etype),
                    ('{0}!_{1}!_%'.format(type_lookup[etype], mname), mname, mname, mname,
                     side_lookup[side], idversion))
            rows = c.fetchall()

            if self.ev.sender in self.bot.dcc.sockets and self.bot.dcc.sockets[self.ev.sender]:
                lowlimit = 10
                highlimit = 999
            else:
                lowlimit = 1
                highlimit = 10

            if len(rows) > highlimit:
                self.reply(" $BVERY$N ambiguous request $R'%s'$N" % self.ev.msg)
                self.reply(" Found %s possible answers" % len(rows))
                self.reply(" Not displaying any !")
            elif highlimit >= len(rows) > lowlimit:
                self.reply(" Ambiguous request $R'%s'$N" % self.ev.msg)
                self.reply(" Found %s possible answers" % len(rows))
                maxlencsv = max([len('%s.%s' % (row['classname'], row['name'])) for row in rows])
                maxlennotch = max([len('[%s.%s]' % (row['classnotch'], row['notch'])) for row in rows])
                for row in rows:
                    fullcsv = '%s.%s' % (row['classname'], row['name'])
                    fullnotch = '[%s.%s]' % (row['classnotch'], row['notch'])
                    fullsearge = '[%s]' % row['searge']
                    self.reply(" %s %s %s %s %s" % (fullsearge, fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), row['sig'], row['notchsig']))
            elif lowlimit >= len(rows) > 0:
                for row in rows:
                    self.reply(" Side        : $B%s" % side)
                    self.reply(" Name        : $B%s.%s" % (row['classname'], row['name']))
                    self.reply(" Notch       : $B%s.%s" % (row['classnotch'], row['notch']))
                    self.reply(" Searge      : $B%s" % row['searge'])
                    self.reply(" Type/Sig    : $B%s$N | $B%s$N" % (row['sig'], row['notchsig']))
                    if row['desc']:
                        self.reply(" Description : %s" % row['desc'])
            else:
                self.reply(" No result for %s" % self.ev.msg.strip())

    def search(self):
        side_lookup = {'client': 0, 'server': 1}

        msg_split = self.ev.msg.strip().split(None, 1)
        if len(msg_split) != 1:
            self.reply(" Syntax error: $B%s <name>$N" % self.ev.cmd)
            return
        search_str = msg_split[0]

        if self.ev.sender in self.bot.dcc.sockets and self.bot.dcc.sockets[self.ev.sender]:
            highlimit = 100
        else:
            highlimit = 10

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            rows = {'classes': None, 'fields': None, 'methods': None}

            self.reply("$B[ SEARCH RESULTS ]")

            for side in ['client', 'server']:
                c.execute("""
                        SELECT name, notch
                        FROM vclasses
                        WHERE name LIKE ? ESCAPE '!'
                          AND side=? AND versionid=?
                    """,
                    ('%{0}%'.format(search_str),
                     side_lookup[side], idversion))
                rows['classes'] = c.fetchall()

                for etype in ['fields', 'methods']:
                    c.execute("""
                            SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                            FROM v{etype}
                            WHERE name LIKE ? ESCAPE '!'
                              AND side=? AND versionid=?
                        """.format(etype=etype),
                        ('%{0}%'.format(search_str),
                         side_lookup[side], idversion))
                    rows[etype] = c.fetchall()

                if not rows['classes']:
                    self.reply(" [%s][  CLASS] No results" % side.upper())
                else:
                    if len(rows['classes']) > highlimit:
                        self.reply(" [%s][  CLASS] Too many results : %d" % (side.upper(), len(rows['classes'])))
                    else:
                        maxlenname = max([len(row['name']) for row in rows['classes']])
                        maxlennotch = max([len(row['notch']) for row in rows['classes']])
                        for row in rows['classes']:
                            self.reply(" [%s][  CLASS] %s %s" % (side.upper(), row['name'].ljust(maxlenname + 2), row['notch'].ljust(maxlennotch + 2)))

                for etype in ['fields', 'methods']:
                    if not rows[etype]:
                        self.reply(" [%s][%7s] No results" % (side.upper(), etype.upper()))
                    else:
                        if len(rows[etype]) > highlimit:
                            self.reply(" [%s][%7s] Too many results : %d" % (side.upper(), etype.upper(), len(rows[etype])))
                        else:
                            maxlenname = max([len('%s.%s' % (row['classname'], row['name'])) for row in rows[etype]])
                            maxlennotch = max([len('[%s.%s]' % (row['classnotch'], row['notch'])) for row in rows[etype]])
                            for row in rows[etype]:
                                fullname = '%s.%s' % (row['classname'], row['name'])
                                fullnotch = '[%s.%s]' % (row['classnotch'], row['notch'])
                                self.reply(" [%s][%7s] %s %s %s %s" % (side.upper(), etype.upper(), fullname.ljust(maxlenname + 2), fullnotch.ljust(maxlennotch + 2), row['sig'], row['notchsig']))

    def setMember(self, side, etype, forced=False):
        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}

        msg_split = self.ev.msg.strip().split(None, 2)
        if len(msg_split) < 2:
            self.reply(" Syntax error: $B%s <membername> <newname> [newdescription]$N" % self.ev.cmd)
            return

        oldname = msg_split[0]
        newname = msg_split[1]
        newdesc = None
        if len(msg_split) > 2:
            newdesc = msg_split[2]

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ SET %s %s ]" % (side.upper(), etype.upper()))
            if forced:
                self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE !")

            # DON'T ALLOW STRANGE CHARACTERS IN NAMES
            if re.search(r'[^A-Za-z0-9$_]', newname):
                self.reply("$RIllegal character in name")
                return

            ## WE CHECK IF WE ARE NOT CONFLICTING WITH A CLASS NAME ##
            c.execute("""
                    SELECT name
                    FROM vclasses
                    WHERE lower(name)=lower(?)
                      AND side=? AND versionid=?
                """,
                (newname,
                 side_lookup[side], idversion))
            row = c.fetchone()
            if row:
                self.reply("$RIt is illegal to use class names for fields or methods !")
                return

            ## WE CHECK WE ONLY HAVE ONE RESULT ##
            c.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                    FROM v{etype}
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], oldname), oldname,
                 side_lookup[side], idversion))
            rows = c.fetchall()

            if len(rows) > 1:
                self.reply(" Ambiguous request $R'%s'$N" % oldname)
                self.reply(" Found %s possible answers" % len(rows))

                maxlencsv = max([len('%s.%s' % (row['classname'], row['name'])) for row in rows])
                maxlennotch = max([len('[%s.%s]' % (row['classnotch'], row['notch'])) for row in rows])
                for row in rows:
                    fullcsv = '%s.%s' % (row['classname'], row['name'])
                    fullnotch = '[%s.%s]' % (row['classnotch'], row['notch'])
                    self.reply(" %s %s %s" % (fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), row['sig']))
                return
            elif not len(rows):
                self.reply(" No result for %s" % oldname)
                return

            ## WE CHECK THAT WE HAVE A UNIQUE NAME
            if not forced:
                c.execute("""
                        SELECT searge, name
                        FROM vmethods
                        WHERE name=?
                          AND side=? AND versionid=?
                    """,
                    (newname,
                     side_lookup[side], idversion))
                row = c.fetchone()
                if row:
                    self.reply("$RYou are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % row['searge'])
                    return

                c.execute("""
                        SELECT searge, name
                        FROM vfields
                        WHERE name=?
                          AND side=? AND versionid=?
                    """,
                    (newname,
                     side_lookup[side], idversion))
                row = c.fetchone()
                if row:
                    self.reply("$RYou are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % row['searge'])
                    return

            if not forced:
                c.execute("""
                        SELECT searge, name
                        FROM vmethods
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                          AND side=? AND versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], oldname), oldname,
                     side_lookup[side], idversion))
                row = c.fetchone()
                if row and row['searge'] != row['name']:
                    self.reply("$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                    return

                c.execute("""
                        SELECT searge, name
                        FROM vfields
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                          AND side=? AND versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], oldname), oldname,
                     side_lookup[side], idversion))
                row = c.fetchone()
                if row and row['searge'] != row['name']:
                    self.reply("$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                    return

            if len(rows) == 1:
                row = rows[0]
                self.reply("Name     : $B%s => %s" % (row['name'], row['newname']))
                self.reply("$BOld desc$N : %s" % row['desc'])

                if not newdesc and not row['desc']:
                    newdesc = None
                elif not newdesc:
                    newdesc = row['desc'].replace('"', "'")
                elif newdesc == 'None':
                    newdesc = None
                else:
                    newdesc = newdesc.replace('"', "'")

                c.execute("""
                        INSERT INTO {etype}hist
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """.format(etype=etype),
                    (None, int(row['id']), row['name'], row['desc'], newname, newdesc, int(time.time()), self.ev.sender, forced, self.ev.cmd))
                db_con.commit()
                self.reply("$BNew desc$N : %s" % newdesc)

    def portMember(self, side, etype, forced=False):
        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}
        target_side_lookup = {'client': 1, 'server': 0}

        msg_split = self.ev.msg.strip().split(None, 2)
        if len(msg_split) < 2:
            self.reply(" Syntax error: $B%s <origin_member> <target_member>$N" % self.ev.cmd)
            return

        origin = msg_split[0]
        target = msg_split[1]

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ PORT %s %s ]" % (side.upper(), etype.upper()))
            if forced:
                self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE !")

            ## WE CHECK WE ONLY HAVE ONE RESULT ##
            c.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                    FROM v{etype}
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], origin), origin,
                 side_lookup[side], idversion))
            rows = c.fetchall()

            if len(rows) > 1:
                self.reply(" Ambiguous request $R'%s'$N" % origin)
                self.reply(" Found %s possible answers" % len(rows))

                maxlencsv = max([len('%s.%s' % (row['classname'], row['name'])) for row in rows])
                maxlennotch = max([len('[%s.%s]' % (row['classnotch'], row['notch'])) for row in rows])
                for row in rows:
                    fullcsv = '%s.%s' % (row['classname'], row['name'])
                    fullnotch = '[%s.%s]' % (row['classnotch'], row['notch'])
                    self.reply(" %s %s %s" % (fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), row['sig']))
                return
            elif not len(rows):
                self.reply(" No result for %s" % origin)
                return
            src_row = rows[0]

            # DO THE SAME FOR OTHER SIDE #
            c.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                    FROM v{etype}
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], target), target,
                 target_side_lookup[side], idversion))
            rows = c.fetchall()

            if len(rows) > 1:
                self.reply(" Ambiguous request $R'%s'$N" % target)
                self.reply(" Found %s possible answers" % len(rows))

                maxlencsv = max([len('%s.%s' % (row['classname'], row['name'])) for row in rows])
                maxlennotch = max([len('[%s.%s]' % (row['classnotch'], row['notch'])) for row in rows])
                for row in rows:
                    fullcsv = '%s.%s' % (row['classname'], row['name'])
                    fullnotch = '[%s.%s]' % (row['classnotch'], row['notch'])
                    self.reply(" %s %s %s" % (fullcsv.ljust(maxlencsv + 2), fullnotch.ljust(maxlennotch + 2), row['sig']))
                return
            elif not len(rows):
                self.reply(" No result for %s" % target)
                return
            tgt_row = rows[0]

            ## WE CHECK IF WE ARE NOT CONFLICTING WITH A CLASS NAME ##
            c.execute("""
                    SELECT name
                    FROM vclasses
                    WHERE lower(name)=lower(?)
                      AND side=? AND versionid=?
                """,
                (src_row['name'],
                 target_side_lookup[side], idversion))
            row = c.fetchone()
            if row:
                self.reply("$RIt is illegal to use class names for fields or methods !")
                return

            ## WE CHECK THAT WE HAVE A UNIQUE NAME
            if not forced:
                c.execute("""
                        SELECT searge, name
                        FROM vmethods
                        WHERE name=?
                          AND side=? AND versionid=?
                    """,
                    (src_row['name'],
                     target_side_lookup[side], idversion))
                row = c.fetchone()
                if row:
                    self.reply("$RYou are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % row['searge'])
                    return

                c.execute("""
                        SELECT searge, name
                        FROM vfields
                        WHERE name=?
                          AND side=? AND versionid=?
                    """,
                    (src_row['name'],
                     target_side_lookup[side], idversion))
                row = c.fetchone()
                if row:
                    self.reply("$RYou are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % row['searge'])
                    return

            if not forced:
                c.execute("""
                        SELECT searge, name
                        FROM vmethods
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                          AND side=? AND versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], target), target,
                     side_lookup[side], idversion))
                row = c.fetchone()
                if row and row['searge'] != row['name']:
                    self.reply("$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                    return

                c.execute("""
                        SELECT searge, name
                        FROM vfields
                        WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                          AND side=? AND versionid=?
                    """,
                    ('{0}!_{1}!_%'.format(type_lookup[etype], target), target,
                     side_lookup[side], idversion))
                row = c.fetchone()
                if row and row['searge'] != row['name']:
                    self.reply("$RYou are trying to rename an already named member. Please use forced update only if you are certain !")
                    return

            c.execute("""
                    INSERT INTO {etype}hist
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """.format(etype=etype),
                (None, int(tgt_row['id']), tgt_row['name'], tgt_row['desc'], src_row['name'], src_row['desc'], int(time.time()), self.ev.sender, forced, self.ev.cmd))
            db_con.commit()
            self.reply("%s     : $B%s => %s" % (side, origin, target))

    def infoChanges(self, side, etype):
        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}

        msg_split = self.ev.msg.split(None, 1)
        if len(msg_split) != 1:
            self.reply("Syntax error: $B%s <searge|index>" % self.ev.cmd)
            return
        member = msg_split[0]

        with self.db.get_db() as db_con:
            c = db_con.cursor()

            self.reply("$B[ GET CHANGES %s %s ]" % (side.upper(), etype.upper()))

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
            rows = c.fetchall()

            if len(rows) >= 1:
                for row in rows:
                    self.reply("[%s, %s] %s: %s -> %s" % (row['v.mcpversion'], row['timestamp'], row['mh.nick'], row['mh.oldname'], row['mh.newname']))
            else:
                self.reply(" No result for %s" % self.ev.msg.strip())

    def revertChanges(self, side, etype):
        type_lookup = {'methods': 'func', 'fields': 'field'}
        side_lookup = {'client': 0, 'server': 1}

        msg_split = self.ev.msg.split(None, 1)
        if len(msg_split) != 1:
            self.reply("Syntax error: $B%s <searge|index>" % self.ev.cmd)
            return
        member = msg_split[0]

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ REVERT %s %s ]" % (side.upper(), etype.upper()))

            c.execute("""
                    UPDATE {etype}
                    SET dirtyid=0
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(type_lookup[etype], member), member,
                 side_lookup[side], idversion))
            db_con.commit()
            self.reply(" Reverting changes on $B%s$N is done." % member)

    def getlog(self):
        side_lookup = {'client': 0, 'server': 1}

        if self.bot.cnick == 'MCPBot':
            if self.ev.sender not in self.bot.dcc.sockets or not self.bot.dcc.sockets[self.ev.sender]:
                self.reply("$BPlease use DCC for getlog")
                return

        msg_split = self.ev.msg.strip().split(None, 1)
        if len(msg_split) > 1:
            self.reply("Syntax error: $B%s [full]" % self.ev.cmd)
            return
        fulllog = False
        if len(msg_split) == 1:
            if msg_split[0] == 'full':
                fulllog = True

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ LOGS ]")

            for side in ['server', 'client']:
                for etype in ['methods', 'fields']:
                    c.execute("""
                            SELECT m.name, m.searge, m.desc, h.newname, h.newdesc,
                              strftime('%m-%d %H:%M', h.timestamp, 'unixepoch') AS timestamp, h.nick, h.cmd, h.forced
                            FROM {etype} m
                              INNER JOIN {etype}hist h ON h.id=m.dirtyid
                            WHERE m.side=? AND m.versionid=?
                            ORDER BY h.timestamp
                        """.format(etype=etype),
                        (side_lookup[side], idversion))
                    rows = c.fetchall()

                    if rows:
                        maxlennick = max([len(row['h.nick']) for row in rows])
                        maxlensearge = max([len(row['m.searge']) for row in rows])
                        maxlenmname = max([len(row['m.name']) for row in rows])

                        for forcedstatus in [0, 1]:
                            for row in rows:
                                if row['forced'] == forcedstatus:
                                    if fulllog:
                                        self.reply("+ %s, %s, %s" % (row['timestamp'], row['h.nick'], row['h.cmd']))
                                        self.reply("  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), row['searge'].ljust(maxlensearge), row['m.name'].ljust(maxlenmname), row['h.newname']))
                                        self.reply("  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), row['searge'].ljust(maxlensearge), row['m.desc'], row['h.newdesc']))
                                    else:
                                        indexmember = re.search('[0-9]+', row['m.searge']).group()
                                        self.reply("+ %s, %s [%s%s][%5s][%4s] %s => %s" % (row['timestamp'], row['h.nick'].ljust(maxlennick), side[0].upper(), etype[0].upper(), indexmember, row['h.cmd'], row['m.name'].ljust(maxlensearge), row['h.newname']))

    def dbCommit(self, pushforced=False):
        msg_split = self.ev.msg.strip().split(None, 1)
        if len(msg_split):
            self.reply("Syntax error: $B%s" % self.ev.cmd)
            return

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ COMMIT ]")

            nentries = 0
            for etype in ['methods', 'fields']:
                if pushforced:
                    c.execute("""
                            SELECT m.id, h.newname, h.newdesc
                            FROM {etype} m
                              INNER JOIN {etype}hist h ON h.id=m.dirtyid
                            WHERE m.versionid=?
                        """.format(etype=etype),
                        (idversion,))
                else:
                    c.execute("""
                            SELECT m.id, h.newname, h.newdesc
                            FROM {etype} m
                              INNER JOIN {etype}hist h ON h.id=m.dirtyid
                            WHERE NOT h.forced=1
                              AND m.versionid=?
                        """.format(etype=etype),
                        (idversion,))
                rows = c.fetchall()
                nentries += len(rows)

                for row in rows:
                    c.execute("""
                            UPDATE {etype}
                            SET name=?, desc=?, dirtyid=0
                            WHERE id=?
                        """.format(etype=etype),
                        (row['h.newname'], row['h.newdesc'], row['m.id']))

            if nentries:
                c.execute("""
                        INSERT INTO commits
                        VALUES (?, ?, ?)
                    """,
                    (None, int(time.time()), self.ev.sender))
                db_con.commit()
                self.reply(" Committed %d new updates" % nentries)
            else:
                self.reply(" No new entries to commit")

    def altCsv(self):
        msg_split = self.ev.msg.strip().split(None, 1)
        if len(msg_split) > 2:
            self.reply(" Syntax error: $B%s [version]$N" % self.ev.cmd)
            return
        if len(msg_split) == 1:
            version = msg_split[0]
        else:
            version = None

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            if version:
                c.execute("""
                        SELECT id
                        FROM versions
                        WHERE mcpversion=?
                    """,
                    (version,))
                row = c.fetchone()
                if not row:
                    self.reply("Version not recognised.")
                    return
                else:
                    idversion = row['id']

            c.execute("""
                    SELECT mcpversion
                    FROM versions
                    WHERE id=?
                """,
                (idversion,))
            row = c.fetchone()
            mcpversion = row['mcpversion']

            if self.bot.cnick == 'MCPBot':
                trgdir = '/home/mcpfiles/mcprolling_%s/mcp/conf' % mcpversion
            else:
                trgdir = 'devconf'

            methodswriter = csv.DictWriter(open('%s/methods.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
            methodswriter.writeheader()
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vmethods
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            rows = c.fetchall()
            for row in rows:
                methodswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

            fieldswriter = csv.DictWriter(open('%s/fields.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
            fieldswriter.writeheader()
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vfields
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            rows = c.fetchall()
            for row in rows:
                fieldswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

            self.reply("New CSVs exported")

    def testCsv(self):
        msg_split = self.ev.msg.strip().split(None, 1)
        if len(msg_split):
            self.reply("Syntax error: $B%s" % self.ev.cmd)
            return

        if self.bot.cnick == 'MCPBot':
            trgdir = '/home/mcpfiles/mcptest'
        else:
            trgdir = 'devconf'

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            methodswriter = csv.DictWriter(open('%s/methods.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
            methodswriter.writeheader()
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vmethods
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            rows = c.fetchall()
            for row in rows:
                methodswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

            fieldswriter = csv.DictWriter(open('%s/fields.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
            fieldswriter.writeheader()
            c.execute("""
                    SELECT DISTINCT searge, name, side, desc
                    FROM vfields
                    WHERE name != classname
                      AND searge != name
                      AND versionid=?
                    ORDER BY side, searge
                """,
                (idversion,))
            rows = c.fetchall()
            for row in rows:
                fieldswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

            self.reply("Test CSVs exported: http://mcp.ocean-labs.de/files/mcptest/")

    def status(self):
        side_lookup = {'client': 0, 'server': 1}

        msg_split = self.ev.msg.strip().split(None, 1)
        if len(msg_split) > 1:
            self.reply("Syntax error: $B%s [full]" % self.ev.cmd)
            return
        full_status = False
        if len(msg_split) == 1:
            if msg_split[0] == 'full':
                full_status = True

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ STATUS ]")

            c.execute("""
                    SELECT mcpversion, botversion, dbversion, clientversion, serverversion
                    FROM versions
                    WHERE id=?
                """,
                (idversion,))
            row = c.fetchone()

            self.reply(" MCP    : $B%s" % row['mcpversion'])
            self.reply(" Bot    : $B%s" % row['botversion'])
            self.reply(" Client : $B%s" % row['clientversion'])
            self.reply(" Server : $B%s" % row['serverversion'])

            if full_status:
                for side in ['client', 'server']:
                    for etype in ['methods', 'fields']:
                        c.execute("""
                                SELECT total({etype}t) AS total, total({etype}r) AS ren, total({etype}u) AS urn
                                FROM vclassesstats
                                WHERE side=? AND versionid=?
                            """.format(etype=etype),
                            (side_lookup[side], idversion))
                        row = c.fetchone()

                        self.reply(" [%s][%7s] : T $B%4d$N | R $B%4d$N | U $B%4d$N | $B%5.2f%%$N" % (side[0].upper(), etype.upper(), row['total'], row['ren'], row['urn'], float(row['ren']) / float(row['total']) * 100))

    def todo(self):
        side_lookup = {'client': 0, 'server': 1}

        msg_split = self.ev.msg.strip().split(None, 1)
        if len(msg_split) != 1:
            self.reply("Syntax error: $B%s <client|server>" % self.ev.cmd)
            return
        search_side = msg_split[0]
        if search_side not in side_lookup:
            self.reply("$Btodo <client|server>")
            return

        with self.db.get_db() as db_con:
            c = db_con.cursor()
            idversion = self.get_version(c)

            self.reply("$B[ TODO %s ]" % search_side.upper())

            c.execute("""
                    SELECT name, methodst+fieldst AS memberst, methodsr+fieldsr AS membersr, methodsu+fieldsu AS membersu
                    FROM vclassesstats
                    WHERE side=? AND versionid=?
                    ORDER BY methodsu+fieldsu DESC
                    LIMIT 10
                """,
                (side_lookup[search_side], idversion))
            rows = c.fetchall()

            for row in rows:
                if row['memberst']:
                    percent = float(row['membersr']) / float(row['memberst']) * 100.0
                else:
                    percent = 0.
                self.reply(" %s : $B%2d$N [ T $B%3d$N | R $B%3d$N | $B%5.2f%%$N ] " % (row['name'].ljust(20), row['membersu'], row['memberst'], row['membersr'], percent))
