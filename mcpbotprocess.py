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
    def __init__(self, cmds, db_con):
        self.evt = cmds.evt
        self.reply = cmds.reply
        self.bot = cmds.bot
        self.db_con = db_con
        self.version_id = self.get_version()

    def get_version(self):
        cur = self.db_con.cursor()
        cur.execute("""
                SELECT value
                FROM config
                WHERE name=:name
            """,
            {'name': 'currentversion'})
        row = cur.fetchone()
        version_id = row['value']
        return version_id

    def set_member(self, oldname, newname, newdesc, side, etype, forced=False):
        cur = self.db_con.cursor()

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
            self.reply("Name     : $B%s => %s" % (row['name'], newname))
            self.reply("$BOld desc$N : %s" % row['desc'])

            if not newdesc and not row['desc']:
                newdesc = None
            elif not newdesc:
                newdesc = row['desc'].replace('"', "'")
            elif newdesc == 'None':
                newdesc = None
            else:
                newdesc = newdesc.replace('"', "'")
            self.reply("$BNew desc$N : %s" % newdesc)

            cur.execute("""
                    INSERT INTO {etype}hist
                    VALUES (:id, :memberid, :oldname, :olddesc, :newname, :newdesc, :timestamp, :nick, :forced, :cmd)
                """.format(etype=etype),
                {'id': None, 'memberid': int(row['id']), 'oldname': row['name'], 'olddesc': row['desc'], 'newname': newname, 'newdesc': newdesc, 'timestamp': int(time.time()), 'nick': self.evt.sender, 'forced': forced, 'cmd': self.evt.cmd})

    def port_member(self, origin, target, side, etype, forced=False):
        target_side_lookup = {'client': 1, 'server': 0}

        cur = self.db_con.cursor()

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
