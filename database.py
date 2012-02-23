import sqlite3
import threading
from contextlib import closing


#====================== DB Decorator ===================================
def database(f):
    def wrap_f(*args, **kwargs):
        if not 'DBLock' in globals():
            globals()['DBLock'] = threading.Lock()

        try:
            DBLock.acquire()
            with sqlite3.connect('database.sqlite') as con:
                con.text_factory = sqlite3.OptimizedUnicode
                with closing(con.cursor()) as cur:
                    (idversion,) = cur.execute("""SELECT value FROM config WHERE name='currentversion'""").fetchone()

                    kwargs['cursor'] = cur
                    kwargs['idvers'] = idversion
                    f(*args, **kwargs)
            DBLock.release()
        except Exception:
            DBLock.release()
            raise
    return wrap_f
