import csv
import re
import time

SIDE_LOOKUP = {'client': 0, 'server': 1}
TYPE_LOOKUP = {'methods': 'func', 'fields': 'field'}


class Error(Exception):
    pass


class CmdError(Error):
    def __init__(self, msg):
        Error.__init__(self)
        self.msg = msg

    def __str__(self):
        return 'Error: $R{msg}'.format(msg=self.msg)


class CmdSyntaxError(CmdError):
    def __init__(self, cmd, msg=''):
        CmdError.__init__(self, msg)
        self.cmd = cmd

    def __str__(self):
        return 'Syntax error: $B{cmd} {msg}'.format(cmd=self.cmd, msg=self.msg)


class MCPBotProcess(object):
    def __init__(self, cmds, db):
        self.commands = cmds
        self.ev = self.commands.ev
        self.reply = self.commands.reply
        self.bot = self.commands.bot
        self.check_args = self.commands.check_args
        self.db = db
        self.version_id = self.get_version()

    def get_version(self):
        c = self.db.cursor()
        c.execute("""
                SELECT value
                FROM config
                WHERE name='currentversion'
            """)
        row = c.fetchone()
        version_id = row['value']
        return version_id

    def get_class(self, search_class, side):
        c = self.db.cursor()

        c.execute("""
                SELECT name, notch, supername
                FROM vclasses
                WHERE (name=? OR notch=?)
                  AND side=? AND versionid=?
            """,
            (search_class, search_class,
             SIDE_LOOKUP[side], self.version_id))
        class_rows = c.fetchall()

        if not class_rows:
            self.reply(" No results found for $B%s" % search_class)
            return

        for class_row in class_rows:
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
                 SIDE_LOOKUP[side], self.version_id))
            const_rows = c.fetchall()

            for const_row in const_rows:
                self.reply(" Constructor : $B%s$N | $B%s$N" % (const_row['sig'], const_row['notchsig']))

    def get_member(self, cname, mname, sname, side, etype):
        if self.ev.sender in self.bot.dcc.sockets and self.bot.dcc.sockets[self.ev.sender]:
            lowlimit = 10
            highlimit = 999
        else:
            lowlimit = 1
            highlimit = 10

        c = self.db.cursor()

        if cname and sname:
            c.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                      AND (classname=? OR classnotch=?)
                      AND (sig=? OR notchsig=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], mname), mname, mname, mname, cname, cname, sname, sname,
                 SIDE_LOOKUP[side], self.version_id))
        elif cname and not sname:
            c.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                      AND (classname=? OR classnotch=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], mname), mname, mname, mname, cname, cname,
                 SIDE_LOOKUP[side], self.version_id))
        elif not cname and sname:
            c.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                      AND (sig=? OR notchsig=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], mname), mname, mname, mname, sname, sname,
                 SIDE_LOOKUP[side], self.version_id))
        else:
            c.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=? OR notch=? OR name=?)
                      AND side=? AND versionid=?
                """.format(etype=etype),
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], mname), mname, mname, mname,
                 SIDE_LOOKUP[side], self.version_id))
        rows = c.fetchall()

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

    def search(self, search_str):
        if self.ev.sender in self.bot.dcc.sockets and self.bot.dcc.sockets[self.ev.sender]:
            highlimit = 100
        else:
            highlimit = 10

        c = self.db.cursor()

        rows = {'classes': None, 'fields': None, 'methods': None}

        for side in ['client', 'server']:
            c.execute("""
                    SELECT name, notch
                    FROM vclasses
                    WHERE name LIKE ? ESCAPE '!'
                      AND side=? AND versionid=?
                """,
                ('%{0}%'.format(search_str),
                 SIDE_LOOKUP[side], self.version_id))
            rows['classes'] = c.fetchall()

            for etype in ['fields', 'methods']:
                c.execute("""
                        SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                        FROM v{etype}
                        WHERE name LIKE ? ESCAPE '!'
                          AND side=? AND versionid=?
                    """.format(etype=etype),
                    ('%{0}%'.format(search_str),
                     SIDE_LOOKUP[side], self.version_id))
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

    def set_member(self, oldname, newname, newdesc, side, etype, forced=False):
        c = self.db.cursor()

        if forced:
            self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE !")

        # DON'T ALLOW STRANGE CHARACTERS IN NAMES
        if re.search(r'[^A-Za-z0-9$_]', newname):
            raise CmdError("Illegal character in name")

        ## WE CHECK IF WE ARE NOT CONFLICTING WITH A CLASS NAME ##
        c.execute("""
                SELECT name
                FROM vclasses
                WHERE lower(name)=lower(?)
                  AND side=? AND versionid=?
            """,
            (newname,
             SIDE_LOOKUP[side], self.version_id))
        row = c.fetchone()
        if row:
            raise CmdError("It is illegal to use class names for fields or methods !")

        ## WE CHECK WE ONLY HAVE ONE RESULT ##
        c.execute("""
                SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                FROM v{etype}
                WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                  AND side=? AND versionid=?
            """.format(etype=etype),
            ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], oldname), oldname,
             SIDE_LOOKUP[side], self.version_id))
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
                 SIDE_LOOKUP[side], self.version_id))
            row = c.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % row['searge'])

            c.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE name=?
                      AND side=? AND versionid=?
                """,
                (newname,
                 SIDE_LOOKUP[side], self.version_id))
            row = c.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % row['searge'])

        if not forced:
            c.execute("""
                    SELECT searge, name
                    FROM vmethods
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """,
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], oldname), oldname,
                 SIDE_LOOKUP[side], self.version_id))
            row = c.fetchone()
            if row and row['searge'] != row['name']:
                raise CmdError("You are trying to rename an already named member. Please use forced update only if you are certain !")

            c.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """,
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], oldname), oldname,
                 SIDE_LOOKUP[side], self.version_id))
            row = c.fetchone()
            if row and row['searge'] != row['name']:
                raise CmdError("You are trying to rename an already named member. Please use forced update only if you are certain !")

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
            self.reply("$BNew desc$N : %s" % newdesc)

    def port_member(self, origin, target, side, etype, forced=False):
        target_side_lookup = {'client': 1, 'server': 0}

        c = self.db.cursor()

        if forced:
            self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE !")

        ## WE CHECK WE ONLY HAVE ONE RESULT ##
        c.execute("""
                SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                FROM v{etype}
                WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                  AND side=? AND versionid=?
            """.format(etype=etype),
            ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], origin), origin,
             SIDE_LOOKUP[side], self.version_id))
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
            ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], target), target,
             target_side_lookup[side], self.version_id))
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
             target_side_lookup[side], self.version_id))
        row = c.fetchone()
        if row:
            raise CmdError("It is illegal to use class names for fields or methods !")

        ## WE CHECK THAT WE HAVE A UNIQUE NAME
        if not forced:
            c.execute("""
                    SELECT searge, name
                    FROM vmethods
                    WHERE name=?
                      AND side=? AND versionid=?
                """,
                (src_row['name'],
                 target_side_lookup[side], self.version_id))
            row = c.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % row['searge'])

            c.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE name=?
                      AND side=? AND versionid=?
                """,
                (src_row['name'],
                 target_side_lookup[side], self.version_id))
            row = c.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % row['searge'])

        if not forced:
            c.execute("""
                    SELECT searge, name
                    FROM vmethods
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """,
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], target), target,
                 SIDE_LOOKUP[side], self.version_id))
            row = c.fetchone()
            if row and row['searge'] != row['name']:
                raise CmdError("You are trying to rename an already named member. Please use forced update only if you are certain !")

            c.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                      AND side=? AND versionid=?
                """,
                ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], target), target,
                 SIDE_LOOKUP[side], self.version_id))
            row = c.fetchone()
            if row and row['searge'] != row['name']:
                raise CmdError("You are trying to rename an already named member. Please use forced update only if you are certain !")

        c.execute("""
                INSERT INTO {etype}hist
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """.format(etype=etype),
            (None, int(tgt_row['id']), tgt_row['name'], tgt_row['desc'], src_row['name'], src_row['desc'], int(time.time()), self.ev.sender, forced, self.ev.cmd))
        self.reply("%s     : $B%s => %s" % (side, origin, target))

    def log_member(self, member, side, etype):
        c = self.db.cursor()

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
            ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], member), member, member, member,
             SIDE_LOOKUP[side]))
        rows = c.fetchall()

        if rows:
            for row in rows:
                self.reply("[%s, %s] %s: %s -> %s" % (row['mcpversion'], row['timestamp'], row['nick'], row['oldname'], row['newname']))
        else:
            self.reply(" No result for %s" % self.ev.msg.strip())

    def revert_member(self, member, side, etype):
        c = self.db.cursor()

        c.execute("""
                UPDATE {etype}
                SET dirtyid=0
                WHERE (searge LIKE ? ESCAPE '!' OR searge=?)
                  AND side=? AND versionid=?
            """.format(etype=etype),
            ('{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], member), member,
             SIDE_LOOKUP[side], self.version_id))
        self.reply(" Reverting changes on $B%s$N is done." % member)

    def get_log(self, full_log):
        if self.bot.cnick == 'MCPBot':
            if self.ev.sender not in self.bot.dcc.sockets or not self.bot.dcc.sockets[self.ev.sender]:
                self.reply("$BPlease use DCC for getlog")
                return

        c = self.db.cursor()

        for side in ['client', 'server']:
            for etype in ['methods', 'fields']:
                c.execute("""
                        SELECT m.name, m.searge, m.desc, h.newname, h.newdesc,
                          strftime('%m-%d %H:%M', h.timestamp, 'unixepoch') AS timestamp, h.nick, h.cmd, h.forced
                        FROM {etype} m
                          INNER JOIN {etype}hist h ON h.id=m.dirtyid
                        WHERE m.side=? AND m.versionid=?
                        ORDER BY h.timestamp
                    """.format(etype=etype),
                    (SIDE_LOOKUP[side], self.version_id))
                rows = c.fetchall()

                if rows:
                    maxlennick = max([len(row['nick']) for row in rows])
                    maxlensearge = max([len(row['searge']) for row in rows])
                    maxlenmname = max([len(row['name']) for row in rows])

                    for forcedstatus in [0, 1]:
                        for row in rows:
                            if row['forced'] == forcedstatus:
                                if full_log:
                                    self.reply("+ %s, %s, %s" % (row['timestamp'], row['nick'], row['cmd']))
                                    self.reply("  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), row['searge'].ljust(maxlensearge), row['name'].ljust(maxlenmname), row['newname']))
                                    self.reply("  [%s%s][%s] %s => %s" % (side[0].upper(), etype[0].upper(), row['searge'].ljust(maxlensearge), row['desc'], row['newdesc']))
                                else:
                                    indexmember = re.search('[0-9]+', row['searge']).group()
                                    self.reply("+ %s, %s [%s%s][%5s][%4s] %s => %s" % (row['timestamp'], row['nick'].ljust(maxlennick), side[0].upper(), etype[0].upper(), indexmember, row['cmd'], row['name'].ljust(maxlensearge), row['newname']))

    def db_commit(self, forced=False):
        c = self.db.cursor()

        nentries = 0
        for etype in ['methods', 'fields']:
            if forced:
                c.execute("""
                        SELECT m.id, h.newname, h.newdesc
                        FROM {etype} m
                          INNER JOIN {etype}hist h ON h.id=m.dirtyid
                        WHERE m.versionid=?
                    """.format(etype=etype),
                    (self.version_id,))
            else:
                c.execute("""
                        SELECT m.id, h.newname, h.newdesc
                        FROM {etype} m
                          INNER JOIN {etype}hist h ON h.id=m.dirtyid
                        WHERE NOT h.forced=1
                          AND m.versionid=?
                    """.format(etype=etype),
                    (self.version_id,))
            rows = c.fetchall()
            nentries += len(rows)

            for row in rows:
                c.execute("""
                        UPDATE {etype}
                        SET name=?, desc=?, dirtyid=0
                        WHERE id=?
                    """.format(etype=etype),
                    (row['newname'], row['newdesc'], row['id']))

        if nentries:
            c.execute("""
                    INSERT INTO commits
                    VALUES (?, ?, ?)
                """,
                (None, int(time.time()), self.ev.sender))
            self.reply(" Committed %d new updates" % nentries)
        else:
            self.reply(" No new entries to commit")

    def alt_csv(self):
        c = self.db.cursor()

        c.execute("""
                SELECT mcpversion
                FROM versions
                WHERE id=?
            """,
            (self.version_id,))
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
            (self.version_id,))
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
            (self.version_id,))
        rows = c.fetchall()
        for row in rows:
            fieldswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

        self.reply("New CSVs exported")

    def test_csv(self):
        if self.bot.cnick == 'MCPBot':
            trgdir = '/home/mcpfiles/mcptest'
        else:
            trgdir = 'devconf'

        c = self.db.cursor()

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
            (self.version_id,))
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
            (self.version_id,))
        rows = c.fetchall()
        for row in rows:
            fieldswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

        self.reply("Test CSVs exported: http://mcp.ocean-labs.de/files/mcptest/")

    def status(self, full_status=False):
        c = self.db.cursor()

        c.execute("""
                SELECT mcpversion, botversion, dbversion, clientversion, serverversion
                FROM versions
                WHERE id=?
            """,
            (self.version_id,))
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
                        (SIDE_LOOKUP[side], self.version_id))
                    row = c.fetchone()

                    self.reply(" [%s][%7s] : T $B%4d$N | R $B%4d$N | U $B%4d$N | $B%5.2f%%$N" % (side[0].upper(), etype.upper(), row['total'], row['ren'], row['urn'], float(row['ren']) / float(row['total']) * 100))

    def todo(self, search_side):
        c = self.db.cursor()

        c.execute("""
                SELECT name, methodst+fieldst AS memberst, methodsr+fieldsr AS membersr, methodsu+fieldsu AS membersu
                FROM vclassesstats
                WHERE side=? AND versionid=?
                ORDER BY methodsu+fieldsu DESC
                LIMIT 10
            """,
            (SIDE_LOOKUP[search_side], self.version_id))
        rows = c.fetchall()

        for row in rows:
            if row['memberst']:
                percent = float(row['membersr']) / float(row['memberst']) * 100.0
            else:
                percent = 0.
            self.reply(" %s : $B%2d$N [ T $B%3d$N | R $B%3d$N | $B%5.2f%%$N ] " % (row['name'].ljust(20), row['membersu'], row['memberst'], row['membersr'], percent))
