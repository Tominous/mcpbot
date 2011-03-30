import sqlite3

#====================== DB Decorator ===================================
def database(f):
    def warp_f(*args, **kwargs):
        dbase = sqlite3.connect('database.sqlite')
        #dbase.isolation_level = None
        c = dbase.cursor()        
        
        (idversion,) = c.execute("""SELECT value FROM config WHERE name='currentversion'""").fetchone()
        
        kwargs['cursor'] = c
        kwargs['idvers'] = idversion

        rows = f(*args, **kwargs)

        dbase.commit()
        c.close()
        dbase.close()
        return rows
    return warp_f    

