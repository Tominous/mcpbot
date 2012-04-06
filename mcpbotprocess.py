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
        self.evt = self.commands.evt
        self.reply = self.commands.reply
        self.bot = self.commands.bot
        self.check_args = self.commands.check_args
        self.db = db
        self.version_id = self.get_version()

    def get_version(self):
        cur = self.db.cursor()
        cur.execute("""
                SELECT value
                FROM config
                WHERE name=:name
            """,
            {'name': 'currentversion'})
        row = cur.fetchone()
        version_id = row['value']
        return version_id

    def get_class(self, search_class, side):
        cur = self.db.cursor()

        cur.execute("""
                SELECT name, notch, supername
                FROM vclasses
                WHERE (name=:search_class OR notch=:search_class)
                  AND side=:side AND versionid=:version
            """,
            {'search_class': search_class,
             'side': SIDE_LOOKUP[side], 'version': self.version_id})
        class_rows = cur.fetchall()

        if not class_rows:
            self.reply(" No results found for $B%s" % search_class)
            return

        for class_row in class_rows:
            self.reply(" Side        : $B%s" % side)
            self.reply(" Name        : $B%s" % class_row['name'])
            self.reply(" Notch       : $B%s" % class_row['notch'])
            self.reply(" Super       : $B%s" % class_row['supername'])

            cur.execute("""
                    SELECT sig, notchsig
                    FROM vconstructors
                    WHERE (name=:search_class OR notch=:search_class)
                      AND side=:side AND versionid=:version
                """,
                {'search_class': search_class,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            const_rows = cur.fetchall()

            for const_row in const_rows:
                self.reply(" Constructor : $B%s$N | $B%s$N" % (const_row['sig'], const_row['notchsig']))

    def get_member(self, cname, mname, sname, side, etype):
        if self.evt.sender in self.bot.dcc.sockets and self.bot.dcc.sockets[self.evt.sender]:
            lowlimit = 10
            highlimit = 999
        else:
            lowlimit = 1
            highlimit = 10

        cur = self.db.cursor()

        mname_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], mname)

        if cname and sname:
            cur.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND (classname=:cname OR classnotch=:cname)
                      AND (sig=:sname OR notchsig=:sname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype),
                {'mname_esc': mname_esc, 'mname': mname, 'cname': cname, 'sname': sname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        elif cname and not sname:
            cur.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND (classname=:cname OR classnotch=:cname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype),
                {'mname_esc': mname_esc, 'mname': mname, 'cname': cname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        elif not cname and sname:
            cur.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND (sig=:sname OR notchsig=:sname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype),
                {'mname_esc': mname_esc, 'mname': mname, 'sname': sname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        else:
            cur.execute("""
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype),
                {'mname_esc': mname_esc, 'mname': mname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        rows = cur.fetchall()

        if len(rows) > highlimit:
            self.reply(" $BVERY$N ambiguous request $R'%s'$N" % self.evt.msg)
            self.reply(" Found %s possible answers" % len(rows))
            self.reply(" Not displaying any !")
        elif highlimit >= len(rows) > lowlimit:
            self.reply(" Ambiguous request $R'%s'$N" % self.evt.msg)
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
            self.reply(" No result for %s" % self.evt.msg.strip())

    def search(self, search_str):
        if self.evt.sender in self.bot.dcc.sockets and self.bot.dcc.sockets[self.evt.sender]:
            highlimit = 100
        else:
            highlimit = 10

        cur = self.db.cursor()

        rows = {'classes': None, 'fields': None, 'methods': None}

        search_esc = '%{0}%'.format(search_str)
        for side in ['client', 'server']:
            cur.execute("""
                    SELECT name, notch
                    FROM vclasses
                    WHERE name LIKE :search_esc ESCAPE '!'
                      AND side=:side AND versionid=:version
                """,
                {'search_esc': search_esc,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            rows['classes'] = cur.fetchall()

            for etype in ['fields', 'methods']:
                cur.execute("""
                        SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                        FROM v{etype}
                        WHERE name LIKE :search_esc ESCAPE '!'
                          AND side=:side AND versionid=:version
                    """.format(etype=etype),
                    {'search_esc': search_esc,
                     'side': SIDE_LOOKUP[side], 'version': self.version_id})
                rows[etype] = cur.fetchall()

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
        cur = self.db.cursor()

        if forced:
            self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE !")

        # DON'T ALLOW STRANGE CHARACTERS IN NAMES
        if re.search(r'[^A-Za-z0-9$_]', newname):
            raise CmdError("Illegal character in name")

        ## WE CHECK IF WE ARE NOT CONFLICTING WITH A CLASS NAME ##
        cur.execute("""
                SELECT name
                FROM vclasses
                WHERE lower(name)=lower(:newname)
                  AND side=:side AND versionid=:version
            """,
            {'newname': newname,
             'side': SIDE_LOOKUP[side], 'version': self.version_id})
        row = cur.fetchone()
        if row:
            raise CmdError("It is illegal to use class names for fields or methods !")

        ## WE CHECK WE ONLY HAVE ONE RESULT ##
        oldname_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], oldname)
        cur.execute("""
                SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                FROM v{etype}
                WHERE (searge LIKE :oldname_esc ESCAPE '!' OR searge=:oldname)
                  AND side=:side AND versionid=:version
            """.format(etype=etype),
            {'oldname_esc': oldname_esc, 'oldname': oldname,
             'side': SIDE_LOOKUP[side], 'version': self.version_id})
        rows = cur.fetchall()

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
            cur.execute("""
                    SELECT searge, name
                    FROM vmethods
                    WHERE name=:newname
                      AND side=:side AND versionid=:version
                """,
                {'newname': newname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            row = cur.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % row['searge'])

            cur.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE name=:newname
                      AND side=:side AND versionid=:version
                """,
                {'newname': newname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            row = cur.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % row['searge'])

        if not forced:
            cur.execute("""
                    SELECT searge, name
                    FROM vmethods
                    WHERE (searge LIKE :oldname_esc ESCAPE '!' OR searge=:oldname)
                      AND side=:side AND versionid=:version
                """,
                {'oldname_esc': oldname_esc, 'oldname': oldname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            row = cur.fetchone()
            if row and row['searge'] != row['name']:
                raise CmdError("You are trying to rename an already named member. Please use forced update only if you are certain !")

            cur.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE (searge LIKE :oldname_esc ESCAPE '!' OR searge=:oldname)
                      AND side=:side AND versionid=:version
                """,
                {'oldname_esc': oldname_esc, 'oldname': oldname,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            row = cur.fetchone()
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

            cur.execute("""
                    INSERT INTO {etype}hist
                    VALUES (:id, :memberid, :oldname, :olddesc, :newname, :newdesc, :timestamp, :nick, :forced, :cmd)
                """.format(etype=etype),
                {'id': None, 'memberid': int(row['id']), 'oldname': row['name'], 'olddesc': row['desc'], 'newname': newname, 'newdesc': newdesc, 'timestamp': int(time.time()), 'nick': self.evt.sender, 'forced': forced, 'cmd': self.evt.cmd})
            self.reply("$BNew desc$N : %s" % newdesc)

    def port_member(self, origin, target, side, etype, forced=False):
        target_side_lookup = {'client': 1, 'server': 0}

        cur = self.db.cursor()

        if forced:
            self.reply("$RCAREFUL, YOU ARE FORCING AN UPDATE !")

        ## WE CHECK WE ONLY HAVE ONE RESULT ##
        origin_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], origin)
        cur.execute("""
                SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                FROM v{etype}
                WHERE (searge LIKE :origin_esc ESCAPE '!' OR searge=:origin)
                  AND side=:side AND versionid=:version
            """.format(etype=etype),
            {'origin_esc': origin_esc, 'origin': origin,
             'side': SIDE_LOOKUP[side], 'version': self.version_id})
        rows = cur.fetchall()

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
        target_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], target)
        cur.execute("""
                SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch, id
                FROM v{etype}
                WHERE (searge LIKE :target_esc ESCAPE '!' OR searge=:target)
                  AND side=:side AND versionid=:version
            """.format(etype=etype),
            {'target_esc': target_esc, 'target': target,
             'side': target_side_lookup[side], 'version': self.version_id})
        rows = cur.fetchall()

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
        cur.execute("""
                SELECT name
                FROM vclasses
                WHERE lower(name)=lower(:name)
                  AND side=:side AND versionid=:version
            """,
            {'name': src_row['name'],
             'side': target_side_lookup[side], 'version': self.version_id})
        row = cur.fetchone()
        if row:
            raise CmdError("It is illegal to use class names for fields or methods !")

        ## WE CHECK THAT WE HAVE A UNIQUE NAME
        if not forced:
            cur.execute("""
                    SELECT searge, name
                    FROM vmethods
                    WHERE name=:name
                      AND side=:side AND versionid=:version
                """,
                {'name': src_row['name'],
                 'side': target_side_lookup[side], 'version': self.version_id})
            row = cur.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other method: %s. Please use forced update only if you are certain !" % row['searge'])

            cur.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE name=:name
                      AND side=:side AND versionid=:version
                """,
                {'name': src_row['name'],
                 'side': target_side_lookup[side], 'version': self.version_id})
            row = cur.fetchone()
            if row:
                raise CmdError("You are conflicting with at least one other field: %s. Please use forced update only if you are certain !" % row['searge'])

        if not forced:
            cur.execute("""
                    SELECT searge, name
                    FROM vmethods
                    WHERE (searge LIKE :target_esc ESCAPE '!' OR searge=:target)
                      AND side=:side AND versionid=:version
                """,
                {'target_esc': target_esc, 'target': target,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            row = cur.fetchone()
            if row and row['searge'] != row['name']:
                raise CmdError("You are trying to rename an already named member. Please use forced update only if you are certain !")

            cur.execute("""
                    SELECT searge, name
                    FROM vfields
                    WHERE (searge LIKE :target_esc ESCAPE '!' OR searge=:target)
                      AND side=:side AND versionid=:version
                """,
                {'target_esc': target_esc, 'target': target,
                 'side': SIDE_LOOKUP[side], 'version': self.version_id})
            row = cur.fetchone()
            if row and row['searge'] != row['name']:
                raise CmdError("You are trying to rename an already named member. Please use forced update only if you are certain !")

        cur.execute("""
                INSERT INTO {etype}hist
                VALUES (:id, :memberid, :oldname, :olddesc, :newname, :newdesc, :timestamp, :nick, :forced, :cmd)
            """.format(etype=etype),
            {'id': None, 'memberid': int(tgt_row['id']), 'oldname': tgt_row['name'], 'olddesc': tgt_row['desc'], 'newname': src_row['name'], 'newdesc': src_row['desc'], 'timestamp': int(time.time()), 'nick': self.evt.sender, 'forced': forced, 'cmd': self.evt.cmd})
        self.reply("%s     : $B%s => %s" % (side, origin, target))

    def log_member(self, member, side, etype):
        cur = self.db.cursor()

        member_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], member)
        cur.execute("""
                    SELECT mh.oldname, mh.olddesc, mh.newname, mh.newdesc,
                      strftime('%m-%d %H:%M', mh.timestamp, 'unixepoch') AS timestamp, mh.nick, mh.forced, m.searge,
                      v.mcpversion
                    FROM {etype} m
                      INNER JOIN versions v ON v.id=m.versionid
                      INNER JOIN {etype}hist mh ON mh.memberid=m.id
                    WHERE (m.searge LIKE :member_esc ESCAPE '!' OR m.searge=:member OR m.notch=:member OR m.name=:member)
                      AND m.side=:side
                """.format(etype=etype),
            {'member_esc': member_esc, 'member': member,
             'side': SIDE_LOOKUP[side]})
        rows = cur.fetchall()

        if rows:
            for row in rows:
                self.reply("[%s, %s] %s: %s -> %s" % (row['mcpversion'], row['timestamp'], row['nick'], row['oldname'], row['newname']))
        else:
            self.reply(" No result for %s" % self.evt.msg.strip())

    def revert_member(self, member, side, etype):
        cur = self.db.cursor()

        member_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], member)
        cur.execute("""
                UPDATE {etype}
                SET dirtyid=0
                WHERE (searge LIKE :member_esc ESCAPE '!' OR searge=:member)
                  AND side=:side AND versionid=:version
            """.format(etype=etype),
            {'member_esc': member_esc, 'member': member,
             'side': SIDE_LOOKUP[side], 'version': self.version_id})
        self.reply(" Reverting changes on $B%s$N is done." % member)

    def get_log(self, full_log):
        if self.bot.cnick == 'MCPBot':
            if self.evt.sender not in self.bot.dcc.sockets or not self.bot.dcc.sockets[self.evt.sender]:
                self.reply("$BPlease use DCC for getlog")
                return

        cur = self.db.cursor()

        for side in ['client', 'server']:
            for etype in ['methods', 'fields']:
                cur.execute("""
                        SELECT m.name, m.searge, m.desc, h.newname, h.newdesc,
                          strftime('%m-%d %H:%M', h.timestamp, 'unixepoch') AS timestamp, h.nick, h.cmd, h.forced
                        FROM {etype} m
                          INNER JOIN {etype}hist h ON h.id=m.dirtyid
                        WHERE m.side=:side AND m.versionid=:version
                        ORDER BY h.timestamp
                    """.format(etype=etype),
                    {'side': SIDE_LOOKUP[side], 'version': self.version_id})
                rows = cur.fetchall()

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
        cur = self.db.cursor()

        nentries = 0
        for etype in ['methods', 'fields']:
            if forced:
                cur.execute("""
                        SELECT m.id, h.newname, h.newdesc
                        FROM {etype} m
                          INNER JOIN {etype}hist h ON h.id=m.dirtyid
                        WHERE m.versionid=:version
                    """.format(etype=etype),
                    {'version': self.version_id})
            else:
                cur.execute("""
                        SELECT m.id, h.newname, h.newdesc
                        FROM {etype} m
                          INNER JOIN {etype}hist h ON h.id=m.dirtyid
                        WHERE NOT h.forced=1
                          AND m.versionid=:version
                    """.format(etype=etype),
                    {'version': self.version_id})
            rows = cur.fetchall()
            nentries += len(rows)

            for row in rows:
                cur.execute("""
                        UPDATE {etype}
                        SET name=:newname, desc=:newdesc, dirtyid=0
                        WHERE id=:id
                    """.format(etype=etype),
                    {'newname': row['newname'], 'newdesc': row['newdesc'], 'id': row['id']})

        if nentries:
            cur.execute("""
                    INSERT INTO commits
                    VALUES (:id, :timestamp, :nick)
                """,
                {'id': None, 'timestamp': int(time.time()), 'nick': self.evt.sender})
            self.reply(" Committed %d new updates" % nentries)
        else:
            self.reply(" No new entries to commit")

    def alt_csv(self):
        cur = self.db.cursor()

        cur.execute("""
                SELECT mcpversion
                FROM versions
                WHERE id=:version
            """,
            {'version': self.version_id})
        row = cur.fetchone()
        mcpversion = row['mcpversion']

        if self.bot.cnick == 'MCPBot':
            trgdir = '/home/mcpfiles/mcprolling_%s/mcp/conf' % mcpversion
        else:
            trgdir = 'devconf'

        methodswriter = csv.DictWriter(open('%s/methods.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
        methodswriter.writeheader()
        cur.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vmethods
                WHERE name != classname
                  AND searge != name
                  AND versionid=:version
                ORDER BY side, searge
            """,
            {'version': self.version_id})
        rows = cur.fetchall()
        for row in rows:
            methodswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

        fieldswriter = csv.DictWriter(open('%s/fields.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
        fieldswriter.writeheader()
        cur.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vfields
                WHERE name != classname
                  AND searge != name
                  AND versionid=:version
                ORDER BY side, searge
            """,
            {'version': self.version_id})
        rows = cur.fetchall()
        for row in rows:
            fieldswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

        self.reply("New CSVs exported")

    def test_csv(self):
        if self.bot.cnick == 'MCPBot':
            trgdir = '/home/mcpfiles/mcptest'
        else:
            trgdir = 'devconf'

        cur = self.db.cursor()

        methodswriter = csv.DictWriter(open('%s/methods.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
        methodswriter.writeheader()
        cur.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vmethods
                WHERE name != classname
                  AND searge != name
                  AND versionid=:version
                ORDER BY side, searge
            """,
            {'version': self.version_id})
        rows = cur.fetchall()
        for row in rows:
            methodswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

        fieldswriter = csv.DictWriter(open('%s/fields.csv' % trgdir, 'wb'), ('searge', 'name', 'side', 'desc'))
        fieldswriter.writeheader()
        cur.execute("""
                SELECT DISTINCT searge, name, side, desc
                FROM vfields
                WHERE name != classname
                  AND searge != name
                  AND versionid=:version
                ORDER BY side, searge
            """,
            {'version': self.version_id})
        rows = cur.fetchall()
        for row in rows:
            fieldswriter.writerow({'searge': row['searge'], 'name': row['name'], 'side': row['side'], 'desc': row['desc']})

        self.reply("Test CSVs exported: http://mcp.ocean-labs.de/files/mcptest/")

    def status(self, full_status=False):
        cur = self.db.cursor()

        cur.execute("""
                SELECT mcpversion, botversion, dbversion, clientversion, serverversion
                FROM versions
                WHERE id=:version
            """,
            {'version': self.version_id})
        row = cur.fetchone()

        self.reply(" MCP    : $B%s" % row['mcpversion'])
        self.reply(" Bot    : $B%s" % row['botversion'])
        self.reply(" Client : $B%s" % row['clientversion'])
        self.reply(" Server : $B%s" % row['serverversion'])

        if full_status:
            for side in ['client', 'server']:
                for etype in ['methods', 'fields']:
                    cur.execute("""
                            SELECT total({etype}t) AS total, total({etype}r) AS ren, total({etype}u) AS urn
                            FROM vclassesstats
                            WHERE side=:side AND versionid=:version
                        """.format(etype=etype),
                        {'side': SIDE_LOOKUP[side], 'version': self.version_id})
                    row = cur.fetchone()

                    self.reply(" [%s][%7s] : T $B%4d$N | R $B%4d$N | U $B%4d$N | $B%5.2f%%$N" % (side[0].upper(), etype.upper(), row['total'], row['ren'], row['urn'], float(row['ren']) / float(row['total']) * 100))

    def todo(self, search_side):
        cur = self.db.cursor()

        cur.execute("""
                SELECT name, methodst+fieldst AS memberst, methodsr+fieldsr AS membersr, methodsu+fieldsu AS membersu
                FROM vclassesstats
                WHERE side=:side AND versionid=:version
                ORDER BY methodsu+fieldsu DESC
                LIMIT 10
            """,
            {'side': SIDE_LOOKUP[search_side], 'version': self.version_id})
        rows = cur.fetchall()

        for row in rows:
            if row['memberst']:
                percent = float(row['membersr']) / float(row['memberst']) * 100.0
            else:
                percent = 0.
            self.reply(" %s : $B%2d$N [ T $B%3d$N | R $B%3d$N | $B%5.2f%%$N ] " % (row['name'].ljust(20), row['membersu'], row['memberst'], row['membersr'], percent))
