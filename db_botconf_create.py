########### DB_BOTCONF_CREATE.PY ###############
# Used to create the bot config db             #
# Contains the schemas. No data is added here. #
# External dependencies :                      #
#  + None                                      #
# External files :                             #
#  + None                                      #
# Author  : ProfMobius                         #
# License : GPLv3                              #
################################################

import sqlite3
import os, sys, time, glob
from optparse import OptionParser

def main(options, args):
    starttime = time.time()
    
    db_name = 'ircbot.sqlite'
    if args:
        db_name = args[0]

    if not options.force:
        try:
            os.stat(db_name)
            print '> Database already exists. Abording to prevent destruction of data !'
            print '> Use -f to override this protection.'
            sys.exit(-1)
        except OSError:
            pass
    else:
        try:
            os.remove(db_name)
        except OSError:
            pass        

    conn = sqlite3.connect(db_name)
    c    = conn.cursor()    

    ##################################

    c.execute("""CREATE TABLE nicks(id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                    nick TEXT NOT NULL,
                                    user TEXT,
                                    host TEXT,
                                    timestamp INTEGER NOT NULL,
                                    online    INTEGER NOT NULL,
                                    UNIQUE(nick)
                                    )""")

    c.execute("""CREATE TABLE groups(id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                    name INTEGER NOT NULL,
                                    UNIQUE(name)
                                    )""")

    c.execute("""CREATE TABLE cmdshist (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                    nickid    INTEGER NOT NULL,
                                    cmd       TEXT    NOT NULL,
                                    params    TEXT,
                                    timestamp INTEGER NOT NULL,
                                    FOREIGN KEY(nickid)  REFERENCES nicks(id) ON UPDATE RESTRICT ON DELETE RESTRICT
                                    )""")

    c.execute("""CREATE TABLE notices (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    type      TEXT    NOT NULL,
                                    tag       TEXT    NOT NULL,
                                    content   TEXT    NOT NULL,
                                    timestamp INTEGER NOT NULL,
                                    nickid    INTEGER NOT NULL,
                                    FOREIGN KEY(nickid)  REFERENCES nicks(id) ON UPDATE RESTRICT ON DELETE RESTRICT
                                    )""")
    
    c.execute("""CREATE TABLE logs (id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    type      TEXT NOT NULL,
                                    cmd       TEXT NOT NULL,
                                    sender    TEXT NOT NULL,
                                    target    TEXT,
                                    msg       TEXT,
                                    timestamp INTEGER NOT NULL)""")
                                    
    
    # Contains the list of commands the bot understand. Used for permission setting
    c.execute("""CREATE TABLE commands(id INTEGER PRIMARY KEY AUTOINCREMENT,
                                       cmd TEXT NOT NULL
                                        )""")

    c.execute("""CREATE TABLE usercmdlk(
                                      userid     INT NOT NULL,        
                                      cmdid      INT NOT NULL,
                                      UNIQUE(userid, cmdid),
                                      FOREIGN KEY(userid)  REFERENCES nicks(id)    ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(cmdid)   REFERENCES commands(id) ON UPDATE RESTRICT ON DELETE RESTRICT                                  
                                      )""")    

    c.execute("""CREATE TABLE groupcmdlk(
                                      groupid    INT NOT NULL,        
                                      cmdid      INT NOT NULL,
                                      UNIQUE(groupid, cmdid),
                                      FOREIGN KEY(groupid)  REFERENCES groups(id)   ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(cmdid)    REFERENCES commands(id) ON UPDATE RESTRICT ON DELETE RESTRICT                                  
                                      )""")    

    c.execute("""CREATE TABLE usergrouplk(
                                      userid     INT NOT NULL,        
                                      groupid    INT NOT NULL,
                                      UNIQUE(userid, groupid),
                                      FOREIGN KEY(userid)  REFERENCES users(id)  ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(groupid) REFERENCES groups(id) ON UPDATE RESTRICT ON DELETE RESTRICT                                  
                                      )""")    

    conn.commit()
    c.close()
    conn.close()

    print '> Done in %.2f seconds'%(time.time()-starttime)

if __name__ == '__main__':
    usage = "usage: %prog [dbname] [options]"
    parser = OptionParser(usage=usage)
    parser.add_option("-f", "--force", dest="force", action="store_true", default=False, help="Force overwritting the database.")  
    (options, args) = parser.parse_args()      
    main(options, args)
