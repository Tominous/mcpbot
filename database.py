import sqlite3

#====================== DB Decorator ===================================
def database(f):
    def warp_f(*args):
        dbase = sqlite3.connect('database.sqlite')
        #dbase.isolation_level = None
        c = dbase.cursor()        
        
        args = list(args)
        args.append(c)
        rows = f(*tuple(args))

        dbase.commit()
        c.close()
        dbase.close()
        return rows
    return warp_f    

