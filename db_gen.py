from glob   import glob
from pprint import pprint
from parsers.parsers import parse_csv, parse_rgs
import os,sys
import sqlite3
import time
from sets import Set
import libobfuscathon.class_def.class_def as libof

unrenamed_classes_dir = 'bin'

os.system('rm database.sqlite')
conn = sqlite3.connect('database.sqlite')
c    = conn.cursor()

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
                                    timestamp       INTEGER NOT NULL
                                      )""")                                                                        

dir_lookup   = {'client':'minecraft', 'server':'minecraft_server'}
side_lookup  = {'client':0, 'server':1}
package_list = []
members_list = {'fields':{'client':[], 'server':[]}, 'methods':{'client':[], 'server':[]}}
for side in ['client', 'server']:
    
    classes = {}

    c.execute("""INSERT INTO versions VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (None, '2.9a', '2.0', '1.0', '1.3_01', '1.3', int(time.time())))
    
    #Here we read all the class files
    for path, dirlist, filelist in os.walk(os.path.join(unrenamed_classes_dir,dir_lookup[side])):
        for class_file in glob(os.path.join(path, '*.class')):
            print '+ Reading %s'%class_file
            class_data = libof.ClassDef(class_file)
            
            
            thisclass = {'Name'      :class_data.getClassname().split('/')[-1], 
                          'Package'   :'/'.join(class_data.getClassname().split('/')[:-1]), 
                          'Super'     :class_data.getSuperName(), 
                          'Interfaces':class_data.getInterfacesNames(),
                          'methods'   :class_data.methods,
                          'fields'    :class_data.fields}

            classes[class_data.getClassname()] = thisclass

            if not thisclass['Package'] in package_list:
                package_list.append(thisclass['Package'])

            c.execute("""INSERT OR IGNORE INTO packages VALUES (?,?)""",
                (len(package_list), package_list[-1]))

            #We insert the already available informations in the db
            c.execute("""INSERT INTO classes (id, side, name, isinterf, packageid, versionid) VALUES (?, ?, ?, ?, ?, ?)""",
                (None, side_lookup[side], thisclass['Name'], False, len(package_list), 1))

            #We retrieve the automatic ID
            c.execute("""SELECT id FROM classes WHERE name = ? AND side = ?""", (thisclass['Name'], side_lookup[side]))
            thisclass['Id'] = c.fetchone()[0]

            for mtype in ['fields', 'methods']:

                for member in thisclass[mtype]:
                    searge = member.getName().split()[0]
                    sig    = member.getName().split()[-1].replace('net/minecraft/src/','').replace('net/minecraft/server/','').replace('net/minecraft/client/','')
                    
                    if searge == '<init>':
                        searge = thisclass['Name']
                    if searge == '<clinit>':
                        continue

                    name   = searge
                    
                    #We insert the method only if it has not be inserted before
                    if not (searge+sig) in members_list[mtype][side]:
                        members_list[mtype][side].append(searge+sig)
                        c.execute("""INSERT INTO %s (id, side, searge, name, sig, dirtyid, versionid) VALUES (?, ?, ?, ?, ?, ?, ?)"""%mtype,
                            (None, side_lookup[side], searge, name, sig, 0, 1))

                    #We get the unique id for this method
                    c.execute("""SELECT id FROM %s WHERE searge = ? AND sig = ? AND side = ?"""%mtype, (searge, sig, side_lookup[side]))
                    membid = c.fetchone()[0]
                    
                    #We insert the corresponding key to the methlk
                    c.execute("""INSERT INTO %slk VALUES (?, ?)"""%mtype,
                        (membid, thisclass['Id']))
                        
    for key, class_ in classes.items():
        
        #We get the super class index and put it in the class entry
        c.execute("""SELECT id FROM classes WHERE name = ? AND side = ?""", (class_['Super'].split('/')[-1], side_lookup[side]))
        row = c.fetchone()
        if row:
            superid = row[0]
            c.execute("""UPDATE classes SET superid = ? WHERE id = ?""", (superid, class_['Id']))
        
        #We get the interfaces ids and insert into interflk
        for interface in class_['Interfaces']:
            name = interface.split('/')[-1]
            c.execute("""SELECT id FROM classes WHERE name = ? AND side = ?""", (name, side_lookup[side]))
            
            row = c.fetchone()
            if row :
                interfid = row[0]
                c.execute("""INSERT INTO interfaceslk VALUES (?, ?)""", (class_['Id'], interfid))
conn.commit()

for side in ['client', 'server']:
    rgs_dict = parse_rgs('%s.rgs'%dir_lookup[side])
    for class_ in rgs_dict['class_map']:
        trgname = class_['trg_name']
        c.execute("""UPDATE classes SET notch = ? WHERE name = ? AND side = ?""",(class_['src_name'].split('/')[-1], trgname, side_lookup[side]))

    for method in rgs_dict['method_map']:
        c.execute("""UPDATE methods SET notch = ?, notchsig = ? WHERE searge = ? AND side = ?""",(method['src_name'].split('/')[-1], method['src_sig'], method['trg_name'], side_lookup[side]))

    for field in rgs_dict['field_map']:
        c.execute("""UPDATE fields SET notch = ? WHERE searge = ? AND side = ?""",(field['src_name'].split('/')[-1], field['trg_name'], side_lookup[side]))

conn.commit()

method_csv = parse_csv('methods.csv', 4, ',', ['trashbin',  'searge_c', 'trashbin', 'searge_s',  'full', 'description'])    
field_csv  = parse_csv('fields.csv',  3, ',', ['trashbin',  'trashbin', 'searge_c', 'trashbin',  'trashbin', 'searge_s', 'full', 'description'])    

for method in method_csv:
    if method['description'] == '*': method['description'] = None
    c.execute("""UPDATE methods SET name = ?, desc = ? WHERE searge  = ? AND side = 0""",(method['full'], method['description'], method['searge_c']))    
    c.execute("""UPDATE methods SET name = ?, desc = ? WHERE searge  = ? AND side = 1""",(method['full'], method['description'], method['searge_s']))
    
for field in field_csv:
    if field['description'] == '*': field['description'] = None
    c.execute("""UPDATE fields SET name = ?, desc = ? WHERE searge = ? AND side = 0""",(field['full'], field['description'], field['searge_c']))
    c.execute("""UPDATE fields SET name = ?, desc = ? WHERE searge = ? AND side = 1""",(field['full'], field['description'], field['searge_s']))    

conn.commit()

c.execute("""UPDATE classes SET notch = name WHERE notch ISNULL""")

#We select all the constructors
c.execute("""SELECT m.id, c.notch
             FROM   methods m
             INNER JOIN methodslk ml ON ml.memberid = m.id
             INNER JOIN classes c    ON ml.classid  = c.id
             WHERE m.notch ISNULL AND m.name = c.name""")

rows = c.fetchall()

#We update constructors with the notch class name and than, we fill all the remaining blanks with name
for row in rows:
    c.execute("""UPDATE methods SET notch = ? WHERE id = ?""", (row[1], row[0]))
c.execute("""UPDATE methods SET notch    = name WHERE notch    ISNULL""")
c.execute("""UPDATE methods SET notchsig =  sig WHERE notchsig ISNULL""")
c.execute("""UPDATE fields  SET notch    = name WHERE notch    ISNULL""")
c.execute("""UPDATE fields  SET notchsig =  sig WHERE notchsig ISNULL""")

#We set the isinterf column
c.execute("""SELECT interfid FROM interfaceslk""")
for row in c.fetchall():
    c.execute("""UPDATE classes SET isinterf = ? WHERE id = ?""",(True, row[0]))

for mtype in ['fields', 'methods']:
    print '+ Updating %s TopIDs'%mtype
    #We get all the methods defined in interfaces and set the topid to it.
    c.execute("""SELECT c.id, m.id
                 FROM classes c
                 INNER JOIN %slk lk ON lk.classid = c.id
                 INNER JOIN %s   m ON lk.memberid = m.id
                 WHERE c.isinterf = 1"""%(mtype,mtype))
    for row in c.fetchall():
        c.execute("""UPDATE %s SET topid = ? WHERE id = ?"""%mtype, (row[0], row[1]))

    #We get all the methods which are implemented in classes without a super and we set the top id
    c.execute("""SELECT c.id, m.id
                 FROM   %s m
                 INNER JOIN %slk ml ON ml.memberid = m.id
                 INNER JOIN classes c    ON ml.classid  = c.id
                 WHERE c.superid ISNULL AND m.topid ISNULL"""%(mtype,mtype))

    for row in c.fetchall():
        c.execute("""UPDATE %s SET topid = ? WHERE id = ?"""%mtype, (row[0], row[1]))
     

    #We get all the methods not yet with a top id
    c.execute("""SELECT m.name, m.id FROM %s m WHERE m.topid ISNULL"""%mtype)
    for mid in c.fetchall():
        methodname = mid[0]
        methodid   = mid[1]

        #We get all classes for this method. Also, we drop the interfaces.
        c.execute("""SELECT c.id, c.superid
                    FROM   %s m
                    INNER JOIN %slk ml ON ml.memberid = m.id
                    INNER JOIN classes c    ON ml.classid  = c.id
                    WHERE m.id = ? AND c.isinterf = 0"""%(mtype, mtype), (methodid,))
        rows = c.fetchall()
        classids = [row[0] for row in rows]
        superids = [row[1] for row in rows]
        results  = []
        for row in rows:
            if not row[1] in classids:
                results.append(row[0])
        
        #If we have only one result, this is the top id.
        if len(results) == 1 :
            c.execute("""UPDATE %s SET topid = ? WHERE id = ?"""%mtype, (results[0], methodid))
            
        #If we have more than one result, we have to walk the tree
        if len(results) > 1 :
            c.execute("""SELECT c.id, c.superid FROM classes c WHERE c.isinterf = 0""")
            classsuper = {}
            for row in c.fetchall(): classsuper[row[0]] = row[1]
            deepresults = Set(results)
            for result in results:
                super = classsuper[result]
                while not super == None:
                    if super in results: deepresults.discard(result)
                    super = classsuper[super]
            
            if len(deepresults) == 1:
                c.execute("""UPDATE %s SET topid = ? WHERE id = ?"""%mtype, (list(deepresults)[0], methodid))
            else:
                raise KeyError("WE COULDN'T FIND A TOP ID !")
            
conn.commit()

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
    SELECT m.id, m.side, m.name, m.notch, m.sig, m.notchsig
    FROM methods m
    INNER JOIN classes c
        ON (m.name = c.name AND m.side = c.side)
    """)

#Triggers to mark entries as dirty
for mtype in ['methods', 'fields']:
    c.execute("""CREATE TRIGGER update_%s_dirty AFTER INSERT ON %shist
                BEGIN
                UPDATE %s SET dirtyid = new.id WHERE id = new.memberid;
                END"""%(mtype, mtype, mtype))

conn.commit()
