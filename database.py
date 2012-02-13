import sqlite3
import threading


#====================== DB Decorator ===================================
def database(f):
    def wrap_f(*args, **kwargs):
        if not 'DBLock' in globals():
            globals()['DBLock'] = threading.Lock()

        try:
            DBLock.acquire()
            dbase = sqlite3.connect('database.sqlite')
            c = dbase.cursor()

            (idversion,) = c.execute("""SELECT value FROM config WHERE name='currentversion'""").fetchone()

            kwargs['cursor'] = c
            kwargs['idvers'] = idversion

            rows = f(*args, **kwargs)

            dbase.commit()
            c.close()
            dbase.close()
            DBLock.release()
        except Exception as msg:
            DBLock.release()
            print msg
            raise

        return rows
    return wrap_f
