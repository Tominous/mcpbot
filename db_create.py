################ DB_CREATE.PY ##################
# Used to create the database                  #
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
    
    db_name = 'database.sqlite'
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

    print '> Generating the database named %s'%db_name

    #TABLE classes : table containing classes information
    #side          : 0 client, 1 server
    #name          : full name
    #notch         : notch name
    #superid       : id in classes of the parent
    #topsuperid    : id in classes of the ultimate parent
    #packageid     : id in packages of the class package
    #versionid     : for which version this entry is valid. Also correspond to a entry in versionid
    c.execute("""CREATE TABLE classes(id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                      side        INT,
                                      name       TEXT, 
                                      notch      TEXT,
                                      superid     INT, 
                                      topsuperid  INT,
                                      isinterf    INT,
                                      packageid   INT,
                                      versionid   INT,
                                      FOREIGN KEY(superid)    REFERENCES classes(id)  ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(topsuperid) REFERENCES classes(id)  ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(packageid)  REFERENCES packages(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(versionid)  REFERENCES version(id) ON UPDATE RESTRICT ON DELETE RESTRICT 
                                      )""")

    #TABLE packages : Contains the list of possible packages.
    c.execute("""CREATE TABLE packages(id INTEGER PRIMARY KEY AUTOINCREMENT,
                                       name TEXT)""")

    #TABLE methods : table containing methods information
    #side          : 0 client, 1 server
    #searge        : searge name (func_, field_)
    #name          : full name
    #notch         : notch name
    #sig           : the signature/type
    #notchsig      : the signature/type notch style
    #desc          : current description
    #topid         : top class where the method/field is first defined
    #dirtyid       : id of the most recent history entry. 0 is none
    #versionid     : for which version this entry is valid. Also correspond to a entry in versionid
    c.execute("""CREATE TABLE methods(id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                      side         INT,        
                                      searge      TEXT, 
                                      notch       TEXT, 
                                      name        TEXT, 
                                      sig         TEXT, 
                                      notchsig    TEXT, 
                                      desc        TEXT,
                                      topid        INT, 
                                      dirtyid      INT,
                                      versionid    INT,
                                      FOREIGN KEY(topid)      REFERENCES classes(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(versionid)  REFERENCES version(id) ON UPDATE RESTRICT ON DELETE RESTRICT 
                                      )""")

    c.execute("""CREATE TABLE fields(id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                      side         INT,        
                                      searge      TEXT, 
                                      notch       TEXT, 
                                      name        TEXT, 
                                      sig         TEXT, 
                                      notchsig    TEXT, 
                                      desc        TEXT,
                                      topid        INT, 
                                      dirtyid      INT,
                                      versionid    INT,
                                      FOREIGN KEY(topid)      REFERENCES classes(id) ON UPDATE RESTRICT ON DELETE RESTRICT,                                
                                      FOREIGN KEY(versionid)  REFERENCES version(id) ON UPDATE RESTRICT ON DELETE RESTRICT                                  
                                      )""")

    #TABLE interflk : link between classes and interfaces. Contains a serie of pairs like classid / interfid
    c.execute("""CREATE TABLE interfaceslk (
                                      classid     INT NOT NULL,        
                                      interfid    INT NOT NULL,
                                      UNIQUE(classid, interfid),
                                      FOREIGN KEY(classid)  REFERENCES classes(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(interfid) REFERENCES classes(id) ON UPDATE RESTRICT ON DELETE RESTRICT                                                                         
                                      )""")

    #TABLE methlk : link between methods and classes. Contains a serie of pairs like methodid / classid
    c.execute("""CREATE TABLE methodslk (
                                      memberid     INT NOT NULL,        
                                      classid      INT NOT NULL,
                                      UNIQUE(memberid, classid),
                                      FOREIGN KEY(memberid)  REFERENCES methods(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(classid)   REFERENCES classes(id) ON UPDATE RESTRICT ON DELETE RESTRICT                                   
                                      )""")

    c.execute("""CREATE TABLE fieldslk (
                                      memberid     INT NOT NULL,        
                                      classid      INT NOT NULL,
                                      UNIQUE(memberid, classid),
                                      FOREIGN KEY(memberid)  REFERENCES fields(id) ON UPDATE RESTRICT ON DELETE RESTRICT,
                                      FOREIGN KEY(classid)   REFERENCES classes(id) ON UPDATE RESTRICT ON DELETE RESTRICT                                  
                                      )""")

    c.execute("""CREATE TABLE methodshist(id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                          memberid     INT NOT NULL, 
                                          oldname     TEXT NOT NULL,
                                          olddesc     TEXT, 
                                          newname     TEXT NOT NULL, 
                                          newdesc     TEXT, 
                                          timestamp   INTEGER NOT NULL, 
                                          nick        TEXT NOT NULL,
                                          forced      INT NOT NULL,
                                          cmd         TEXT NOT NULL,
                                          FOREIGN KEY(memberid)  REFERENCES methods(id) ON UPDATE RESTRICT ON DELETE RESTRICT
                                          )""")

    c.execute("""CREATE TABLE fieldshist (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                          memberid     INT NOT NULL, 
                                          oldname     TEXT NOT NULL,
                                          olddesc     TEXT, 
                                          newname     TEXT NOT NULL, 
                                          newdesc     TEXT, 
                                          timestamp   INTEGER NOT NULL, 
                                          nick        TEXT NOT NULL,
                                          forced      INT NOT NULL,
                                          cmd         TEXT NOT NULL,                                          
                                          FOREIGN KEY(memberid)  REFERENCES fields(id) ON UPDATE RESTRICT ON DELETE RESTRICT
                                          )""")
                                          
    c.execute("""CREATE TABLE commits (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                          timestamp   INTEGER NOT NULL, 
                                          nick        TEXT NOT NULL
                                          )""")                                                                        

    c.execute("""CREATE TABLE versions (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                        mcpversion      TEXT NOT NULL,
                                        botversion      TEXT NOT NULL,
                                        dbversion       TEXT NOT NULL,
                                        clientversion   TEXT NOT NULL,
                                        serverversion   TEXT NOT NULL,
                                        timestamp       INTEGER NOT NULL,
                                        UNIQUE(mcpversion, botversion, dbversion, clientversion, serverversion)
                                          )""")        

    c.execute("""CREATE TABLE config (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                                        name   TEXT NOT NULL,
                                        value  TEXT NOT NULL,
                                        UNIQUE(name)
                                        )""")

    ######### WE SETUP SOME CONFIGURATION KEYS #########

    c.execute("""INSERT INTO config (id, name, value) VALUES (?, ?, ?)""", (None, 'currentversion', -1))

    ######### WE NOW DEFINE THE VIEWS WE WILL BE USING ###########

    # For methods and fields, we want id, side, searge, notch, name, sig, notchsig, desc, topclass name, topclass notch, package, version
    for mtype in ['fields', 'methods']:
        c.execute("""CREATE VIEW v%s AS
            SELECT m.id, m.side, m.searge, m.notch, 
            CASE WHEN m.dirtyid > 0 THEN h.newname
                                ELSE m.name
            END AS name,  
            CASE WHEN m.dirtyid > 0 THEN h.newdesc
                                ELSE m.desc
            END AS desc,
                m.sig, m.notchsig, c.name AS classname, c.notch AS classnotch, p.name AS package, c.versionid
        FROM %s m
        INNER JOIN classes c
            ON m.topid = c.id
        INNER JOIN packages p
            ON c.packageid = p.id
        LEFT  JOIN %shist h
            ON m.dirtyid = h.id
        """%(mtype,mtype,mtype))

    for mtype in ['fields', 'methods']:
        c.execute("""CREATE VIEW v%sall AS
            SELECT m.id, m.side, m.searge, m.notch, 
            CASE WHEN m.dirtyid > 0 THEN h.newname
                                ELSE m.name
            END AS name,  
            CASE WHEN m.dirtyid > 0 THEN h.newdesc
                                ELSE m.desc
            END AS desc,
                m.sig, m.notchsig, c.name AS classname, c.notch AS classnotch, c1.name AS topname, c1.notch AS topnotch, p.name AS package, c.versionid
        FROM %s m
        INNER JOIN %slk mlk
            ON mlk.memberid = m.id
        INNER JOIN classes c
            ON mlk.classid = c.id        
        INNER JOIN classes c1
            ON m.topid = c1.id        
        INNER JOIN packages p
            ON c.packageid = p.id
        LEFT  JOIN %shist h
            ON m.dirtyid = h.id
        """%(mtype,mtype,mtype,mtype))
        
    c.execute("""CREATE VIEW vclasses AS
        SELECT c.id, c.side, c.name, c.notch, c1.name AS supername, c.isinterf, p.name AS package, c.versionid
        FROM classes c
        INNER JOIN packages p
            ON c.packageid = p.id
        LEFT JOIN classes c1
            ON c.superid = c1.id 
        """)

    c.execute("""CREATE VIEW vconstructors AS
        SELECT m.id, m.side, m.name, m.notch, m.sig, m.notchsig, m.versionid
        FROM methods m
        INNER JOIN classes c
            ON (m.name = c.name AND m.side = c.side AND m.versionid = c.versionid)
        """)

    c.execute("""CREATE VIEW vclassesstats AS
             SELECT c.id, c.name, 
            (SELECT COUNT(*)
                    FROM classes c1
                    INNER JOIN methods m ON c1.id = m.topid
                    WHERE c1.id = c.id
                    AND NOT m.name = c1.name
                    AND c1.versionid=m.versionid
                    GROUP BY c1.id
            ) as methodst,
            (SELECT COUNT(*)
                    FROM classes c1
                    INNER JOIN methods m ON c1.id = m.topid
                    WHERE c1.id = c.id
                    AND NOT m.name = m.searge
                    AND NOT m.name = c1.name
                    AND c1.versionid=m.versionid
                    GROUP BY c1.id
            ) as methodsr,
            (SELECT COUNT(*)
                    FROM classes c1
                    INNER JOIN methods m ON c1.id = m.topid
                    WHERE c1.id = c.id
                    AND m.name = m.searge
                    AND NOT m.name = c1.name
                    AND c1.versionid=m.versionid
                    GROUP BY c1.id
            ) as methodsu,
            (SELECT COUNT(*)
                    FROM classes c1
                    INNER JOIN fields m ON c1.id = m.topid
                    WHERE c1.id = c.id
                    AND NOT m.name = c1.name
                    AND c1.versionid=m.versionid
                    GROUP BY c1.id
            ) as fieldst,
            (SELECT COUNT(*)
                    FROM classes c1
                    INNER JOIN fields m ON c1.id = m.topid
                    WHERE c1.id = c.id
                    AND NOT m.name = m.searge
                    AND NOT m.name = c1.name
                    AND c1.versionid=m.versionid
                    GROUP BY c1.id
            ) as fieldsr,
            (SELECT COUNT(*)
                    FROM classes c1
                    INNER JOIN fields m ON c1.id = m.topid
                    WHERE c1.id = c.id
                    AND m.name = m.searge
                    AND NOT m.name = c1.name
                    AND c1.versionid=m.versionid
                    GROUP BY c1.id
            ) as fieldsu,            
            c.side, c.versionid
            FROM classes c""")


    ######### THE DB TRIGGERS ###########

    #Triggers to mark entries as dirty
    for mtype in ['methods', 'fields']:
        c.execute("""CREATE TRIGGER update_%s_dirty AFTER INSERT ON %shist
                    BEGIN
                    UPDATE %s SET dirtyid = new.id WHERE id = new.memberid;
                    END"""%(mtype, mtype, mtype))

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
