import sqlite3
import threading
from contextlib import closing


_db_lock = threading.Lock()


#====================== DB Decorator ===================================
def database(f):
    def wrap_f(*args, **kwargs):
        try:
            _db_lock.acquire()
            with sqlite3.connect('database.sqlite') as con:
                con.text_factory = sqlite3.OptimizedUnicode
                with closing(con.cursor()) as cur:
                    (idversion,) = cur.execute("""SELECT value FROM config WHERE name='currentversion'""").fetchone()

                    kwargs['cursor'] = cur
                    kwargs['idvers'] = idversion
                    f(*args, **kwargs)
            _db_lock.release()
        except Exception:
            _db_lock.release()
            raise
    return wrap_f
