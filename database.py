import sqlite3

#====================== DB Decorator ===================================
def database(f):
    def warp_f(*args):
        dbase = sqlite3.connect('database.db')
        c = dbase.cursor()        
        
        args = list(args)
        args.append(c)
        rows = f(*tuple(args))

        dbase.commit()
        c.close()
        dbase.close()
        return rows
    return warp_f    

#====================== DB Access    ===================================
@database
def getMembers(msg, side, etype, c):
    type_lookup = {'method':'func','field':'field'}
    side_lookup = {'client':0, 'server':1}        
    
    if '.' in msg:
        classname  = msg.split('.')[0]
        membername = msg.split('.')[1]
        c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description, m.id, m.dirty
                        FROM %ss m
                        LEFT JOIN classes c  ON m.class   = c.id
                        WHERE ((m.name LIKE ? ESCAPE '!') OR m.notch = ? OR m.decoded = ?) AND m.side = ? AND (c.name = ? OR c.notch = ?)"""%
                        etype,
                        ('%s!_%s!_%%'%(type_lookup[etype], membername), membername, membername, side_lookup[side], classname, classname))
    else:
        c.execute("""SELECT m.name, m.notch, m.decoded, m.signature, m.notchsig, c.name, c.notch, m.description, m.id, m.dirty
                        FROM %ss m 
                        LEFT JOIN classes c  ON m.class   = c.id
                        WHERE ((m.name LIKE ? ESCAPE '!') OR m.notch = ? OR m.decoded = ?) AND m.side = ?"""%etype,
                        ('%s!_%s!_%%'%(type_lookup[etype], msg), msg, msg, side_lookup[side]))
    
    rows = list(c.fetchall())

    for irow in range(len(rows)):
        row = rows[irow]
        if row[9]:
            tablename = '%shist'%etype[0]
            c.execute("""SELECT decoded, description FROM %s WHERE target = ? ORDER BY timestamp"""%tablename, (row[8],))
            update = c.fetchall()[-1] #We grab the last update
            row = list(row)
            row[2] = update[0]
            row[7] = update[1]
            row = tuple(row)
        rows[irow] = row

    return tuple(rows)
