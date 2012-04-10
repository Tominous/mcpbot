import time
import sqlite3
import threading

from contextlib import contextmanager


class DBHandler(object):
    def __init__(self, db_name):
        self._db_lock = threading.Lock()
        self.db_name = db_name

    @contextmanager
    def get_con(self):
        with self._db_lock:
            with sqlite3.connect(self.db_name) as db_con:
                db_con.text_factory = sqlite3.OptimizedUnicode
                db_con.row_factory = sqlite3.Row
                yield db_con

    @staticmethod
    def get_queries(db_con):
        return DBQueries(db_con)


SIDE_LOOKUP = {'client': 0, 'server': 1}
TYPE_LOOKUP = {'methods': 'func', 'fields': 'field'}


class DBQueries(object):
    def __init__(self, db_con):
        self.db_con = db_con
        self.version_id = self.get_version()

    def get_version(self):
        cur = self.db_con.cursor()
        query = """
            SELECT value
            FROM config
            WHERE name=:name
        """
        cur.execute(query, {'name': 'currentversion'})
        row = cur.fetchone()
        version_id = row['value']
        return version_id

    def get_mcpversion(self):
        cur = self.db_con.cursor()
        query = """
            SELECT mcpversion
            FROM versions
            WHERE id=:version
        """
        cur.execute(query, {'version': self.version_id})
        row = cur.fetchone()
        mcpversion = row['mcpversion']
        return mcpversion

    def get_classes(self, search_class, side):
        cur = self.db_con.cursor()
        query = """
            SELECT name, notch, supername
            FROM vclasses
            WHERE (name=:search_class OR notch=:search_class)
              AND side=:side AND versionid=:version
        """
        cur.execute(query, {'search_class': search_class, 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchall()

    def get_constructors(self, search_class, side):
        cur = self.db_con.cursor()
        query = """
            SELECT sig, notchsig
            FROM vconstructors
            WHERE (name=:search_class OR notch=:search_class)
              AND side=:side AND versionid=:version
        """
        cur.execute(query, {'search_class': search_class, 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchall()

    def get_member(self, cname, mname, sname, side, etype):
        cur = self.db_con.cursor()
        mname_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], mname)
        if cname and sname:
            query = """
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND (classname=:cname OR classnotch=:cname)
                      AND (sig=:sname OR notchsig=:sname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype)
        elif cname and not sname:
            query = """
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND (classname=:cname OR classnotch=:cname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype)
        elif not cname and sname:
            query = """
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND (sig=:sname OR notchsig=:sname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype)
        else:
            query = """
                    SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
                    FROM v{etype}
                    WHERE (searge LIKE :mname_esc ESCAPE '!' OR searge=:mname OR notch=:mname OR name=:mname)
                      AND side=:side AND versionid=:version
                """.format(etype=etype)
        cur.execute(query, {'mname_esc': mname_esc, 'mname': mname, 'cname': cname, 'sname': sname, 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchall()

    def search_class(self, search_str, side):
        cur = self.db_con.cursor()
        search_esc = '%{0}%'.format(search_str)
        query = """
            SELECT name, notch
            FROM vclasses
            WHERE name LIKE :search_esc ESCAPE '!'
              AND side=:side AND versionid=:version
        """
        cur.execute(query, {'search_esc': search_esc, 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchall()

    def search_member(self, search_str, side, etype):
        cur = self.db_con.cursor()
        search_esc = '%{0}%'.format(search_str)
        query = """
            SELECT name, notch, searge, sig, notchsig, desc, classname, classnotch
            FROM v{etype}
            WHERE name LIKE :search_esc ESCAPE '!'
              AND side=:side AND versionid=:version
        """.format(etype=etype)
        cur.execute(query, {'search_esc': search_esc, 'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchall()

    def log_member(self, member, side, etype):
        cur = self.db_con.cursor()
        member_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], member)
        query = """
            SELECT mh.oldname, mh.olddesc, mh.newname, mh.newdesc,
              strftime('%m-%d %H:%M', mh.timestamp, 'unixepoch') AS timestamp, mh.nick, mh.forced, m.searge,
              v.mcpversion
            FROM {etype} m
              INNER JOIN versions v ON v.id=m.versionid
              INNER JOIN {etype}hist mh ON mh.memberid=m.id
            WHERE (m.searge LIKE :member_esc ESCAPE '!' OR m.searge=:member OR m.notch=:member OR m.name=:member)
              AND m.side=:side
        """.format(etype=etype)
        cur.execute(query, {'member_esc': member_esc, 'member': member, 'side': SIDE_LOOKUP[side]})
        return cur.fetchall()

    def revert_member(self, member, side, etype):
        cur = self.db_con.cursor()
        member_esc = '{0}!_{1}!_%'.format(TYPE_LOOKUP[etype], member)
        query = """
            UPDATE {etype}
            SET dirtyid=0
            WHERE (searge LIKE :member_esc ESCAPE '!' OR searge=:member)
              AND side=:side AND versionid=:version
        """.format(etype=etype)
        cur.execute(query, {'member_esc': member_esc, 'member': member, 'side': SIDE_LOOKUP[side], 'version': self.version_id})

    def get_log(self, side, etype):
        cur = self.db_con.cursor()
        query = """
            SELECT m.name, m.searge, m.desc, h.newname, h.newdesc,
              strftime('%m-%d %H:%M', h.timestamp, 'unixepoch') AS timestamp, h.nick, h.cmd, h.forced
            FROM {etype} m
              INNER JOIN {etype}hist h ON h.id=m.dirtyid
            WHERE m.side=:side AND m.versionid=:version
            ORDER BY h.timestamp
        """.format(etype=etype)
        cur.execute(query, {'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchall()

    def db_commit(self, forced):
        cur = self.db_con.cursor()

        nentries = 0
        for etype in ['methods', 'fields']:
            if forced:
                query = """
                    SELECT m.id, h.newname, h.newdesc
                    FROM {etype} m
                      INNER JOIN {etype}hist h ON h.id=m.dirtyid
                    WHERE m.versionid=:version
                """.format(etype=etype)
            else:
                query = """
                    SELECT m.id, h.newname, h.newdesc
                    FROM {etype} m
                      INNER JOIN {etype}hist h ON h.id=m.dirtyid
                    WHERE NOT h.forced=1
                      AND m.versionid=:version
                """.format(etype=etype)
            cur.execute(query, {'version': self.version_id})
            rows = cur.fetchall()
            nentries += len(rows)

            for row in rows:
                query = """
                    UPDATE {etype}
                    SET name=:newname, desc=:newdesc, dirtyid=0
                    WHERE id=:id
                """.format(etype=etype)
                cur.execute(query, {'newname': row['newname'], 'newdesc': row['newdesc'], 'id': row['id']})
        return nentries

    def add_commit(self, nick):
        cur = self.db_con.cursor()
        query = """
            INSERT INTO commits
            VALUES (:id, :timestamp, :nick)
        """
        cur.execute(query, {'id': None, 'timestamp': int(time.time()), 'nick': nick})

    def csv_member(self, etype):
        cur = self.db_con.cursor()
        query = """
            SELECT DISTINCT searge, name, side, desc
            FROM v{etype}
            WHERE name != classname
              AND searge != name
              AND versionid=:version
            ORDER BY side, searge
        """.format(etype=etype)
        cur.execute(query, {'version': self.version_id})
        return cur.fetchall()

    def status(self):
        cur = self.db_con.cursor()
        query = """
            SELECT mcpversion, botversion, dbversion, clientversion, serverversion
            FROM versions
            WHERE id=:version
        """
        cur.execute(query, {'version': self.version_id})
        return cur.fetchone()

    def status_members(self, side, etype):
        cur = self.db_con.cursor()
        query = """
            SELECT total({etype}t) AS total, total({etype}r) AS ren, total({etype}u) AS urn
            FROM vclassesstats
            WHERE side=:side AND versionid=:version
        """.format(etype=etype)
        cur.execute(query, {'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchone()

    def todo(self, side):
        cur = self.db_con.cursor()
        query = """
            SELECT name, methodst+fieldst AS memberst, methodsr+fieldsr AS membersr, methodsu+fieldsu AS membersu
            FROM vclassesstats
            WHERE side=:side AND versionid=:version
            ORDER BY methodsu+fieldsu DESC
            LIMIT 10
        """
        cur.execute(query, {'side': SIDE_LOOKUP[side], 'version': self.version_id})
        return cur.fetchall()
