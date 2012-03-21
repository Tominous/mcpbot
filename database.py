import sqlite3
import threading
from contextlib import closing


_db_lock = threading.Lock()


#====================== DB Decorator ===================================
def database(f):
    def wrap_f(*args, **kwargs):
        with _db_lock:
            with sqlite3.connect('database.sqlite') as con:
                con.text_factory = sqlite3.OptimizedUnicode
                with closing(con.cursor()) as cur:
                    result = cur.execute("""
                            SELECT value
                            FROM config
                            WHERE name='currentversion'
                        """).fetchone()
                    (idversion,) = result
                    kwargs['cursor'] = cur
                    kwargs['idvers'] = idversion
                    f(*args, **kwargs)
    return wrap_f
