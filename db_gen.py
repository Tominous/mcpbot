#Code to generate a database from unrenamed class files, a rgs and csv.
#Input :
#   A recompile MC bin directory should be put in bin. Those classes are generated WITHOUT renamer active. (comment out the 3 or 4 last lines of the bash script)

from glob   import glob
from pprint import pprint
from parsers.parsers import parse_csv, parse_rgs
import os,sys
import sqlite3
import libobfuscathon.class_def.class_def as libof

unrenamed_classes_dir = 'bin'

class_id  = 0
field_id  = 0
method_id = 0

os.system('rm database.db')
conn = sqlite3.connect('database.db')
c    = conn.cursor()
c.execute("""create table classes(id INT, side TEXT, name TEXT, notch TEXT, decoded TEXT, super INT, topsuper INT, interface0 INT, interface1 INT, interface2 INT, interface3 INT, interface4 INT, dirty INT, updatetime TEXT)""")
c.execute("""create table methods(id INT, side TEXT, name TEXT, notch TEXT, decoded TEXT, signature TEXT, notchsig TEXT, class INT, implemented INT, inherited INT, defined INT, description TEXT, dirty INT, updatetime TEXT)""")
c.execute("""create table fields(id INT,  side TEXT, name TEXT, notch TEXT, decoded TEXT, signature TEXT, notchsig TEXT, class INT, implemented INT, inherited INT, defined INT, description TEXT, dirty INT, updatetime TEXT)""")

dir_lookup = {'client':'minecraft', 'server':'minecraft_server'}

for side in ['client', 'server']:
    
    fields  = {}
    methods = {}
    classes = {}
    classes_id = {}    
    
    #Here we read all the class files
    for path, dirlist, filelist in os.walk(os.path.join(unrenamed_classes_dir,dir_lookup[side])):
        for class_file in glob(os.path.join(path, '*.class')):
            print '+ Reading %s'%class_file
            class_data = libof.ClassDef(class_file)
            
            classes[class_data.getClassname()] = {'ID'        :class_id, 
                                                  'Name'      :class_data.getClassname(), 
                                                  'Super'     :class_data.getSuperName(), 
                                                  'Interfaces':class_data.getInterfacesNames(),
                                                  'Methods'   :class_data.methods,
                                                  'Fields'    :class_data.fields}
            classes_id[class_id] = classes[class_data.getClassname()]
            class_id += 1
            
            for field in class_data.fields:
                name = field.getName().split()[0]
                sig  = field.getName().split()[1]
                
                fields[field_id] = {'ID':field_id, 'Name':name, 'Signature':sig, 'Class':classes[class_data.getClassname()]['ID'], 'Implemented':True, 'Inherited':-1}
                field_id += 1

            for method in class_data.methods:
                name = method.getName().split()[0]
                sig  = method.getName().split()[1]
                
                if name == '<clinit>' : continue
                
                methods[method_id] = {'ID':method_id, 'Name':name, 'Signature':sig, 'Class':classes[class_data.getClassname()]['ID'], 'Implemented':True, 'Inherited':-1}
                method_id += 1

    #We transform names into id references
    for key, data in classes.items():
        if data['Super'] in classes:
            data['SuperID'] = classes[data['Super']]['ID']
        else: data['SuperID'] = -1
        data['InterfacesID'] = []
        
        if len(data['Interfaces']) > 5:
            raise KeyError('Too many interfaces !')
        
        for interface in data['Interfaces']:
            if interface in classes:
                data['InterfacesID'].append(classes[interface]['ID'])
        while len(data['InterfacesID']) < 5:
            data['InterfacesID'].append(-1)

    #We go up the inheritance tree to find the super super class
    for key, data in classes.items():
        super    = data['SuperID']
        topsuper = -1
        while super != -1:
            super = classes[classes_id[super]['Name']]['SuperID']
            if super != -1: topsuper = super
        data['TopSuperID'] = topsuper

    #We go up the inheritance tree to find the last class defining a given method
    for key, data in methods.items():
        class_id = data['Class']
        found_in = class_id
        super    = classes_id[class_id]['SuperID']
        while super != -1:
            if data['Name'] in [i.getName().split()[0] for i in classes_id[super]['Methods']]:
                found_in = classes_id[super]['ID']
            super = classes_id[super]['SuperID']
        data['Defined'] = found_in

    #We go up the inheritance tree to find the last class defining a given field
    for key, data in fields.items():
        class_id = data['Class']
        found_in = class_id
        super    = classes_id[class_id]['SuperID']
        while super != -1:
            if data['Name'] in [i.getName().split()[0] for i in classes_id[super]['Fields']]:
                found_in = classes_id[super]['ID']
            super = classes_id[super]['SuperID']
        data['Defined'] = found_in

    for key, data in classes.items():
        print '+ Inserting in the db : %s'%key
        c.execute("""insert into classes values (%d, '%s', '%s', '-1', '%s', %d, %d, %d, %d, %d, %d, %d, '-1', '-1')"""%
                (data['ID'], side, data['Name'].split('/')[-1], data['Name'].split('/')[-1], data['SuperID'], data['TopSuperID'], 
                data['InterfacesID'][0], data['InterfacesID'][1], data['InterfacesID'][2], data['InterfacesID'][3], data['InterfacesID'][4]))

    #Inherited is supposed to represent the methods not in the cpool (not implemented), but still available by inheritance.
    for key, data in fields.items():
        print '+ Inserting in the db : %s'%data['Name']
        c.execute("""insert into fields values (%d, '%s', '%s', '-1', '%s', '%s', '-1', %d, %d, %d, %d, '-1', '-1', '-1')"""%
                (data['ID'], side, data['Name'], data['Name'], data['Signature'].replace('net/minecraft/src/',''),  data['Class'], int(data['Implemented']), data['Inherited'], data['Defined']))

    for key, data in methods.items():
        print '+ Inserting in the db : %s'%data['Name']
        c.execute("""insert into methods values (%d, '%s', '%s', '-1', '%s', '%s', '-1', %d, %d, %d, %d, '-1', '-1', '-1')"""%
                (data['ID'], side, data['Name'], data['Name'], data['Signature'].replace('net/minecraft/src/',''),  data['Class'], int(data['Implemented']), data['Inherited'], data['Defined']))

conn.commit()

print "+ Scanning RGS files"
for side in ['client', 'server']:
    rgs_dict = parse_rgs('%s.rgs'%dir_lookup[side])
    for class_ in rgs_dict['class_map']:
        trgname = class_['trg_name']
        c.execute("""UPDATE classes SET notch = '%s' WHERE name = '%s' AND side = '%s'"""%(class_['src_name'].split('/')[-1], trgname, side))

    for method in rgs_dict['method_map']:
        c.execute("""UPDATE methods SET notch = '%s', notchsig = '%s' WHERE name = '%s' AND side = '%s'"""%(method['src_name'].split('/')[-1], method['src_sig'], method['trg_name'], side))

    for field in rgs_dict['field_map']:
        c.execute("""UPDATE fields SET notch = '%s' WHERE name = '%s' AND side = '%s'"""%(field['src_name'].split('/')[-1], field['trg_name'], side))

conn.commit()

method_csv = parse_csv('methods.csv', 4, ',', ['trashbin',  'searge_c', 'trashbin', 'searge_s',  'full', 'description'])    
field_csv  = parse_csv('fields.csv',  3, ',', ['trashbin',  'trashbin', 'searge_c', 'trashbin',  'trashbin', 'searge_s', 'full', 'description'])    

for method in method_csv:
    c.execute("""UPDATE methods SET decoded  = '%s' WHERE name     = '%s' AND side = 'client'"""%(method['full'], method['searge_c']))    
    c.execute("""UPDATE methods SET decoded  = '%s' WHERE name     = '%s' AND side = 'server'"""%(method['full'], method['searge_s']))
    
for field in field_csv:
    c.execute("""UPDATE fields SET decoded = '%s' WHERE name = '%s' AND side = 'client'"""%(field['full'], field['searge_c']))
    c.execute("""UPDATE fields SET decoded = '%s' WHERE name = '%s' AND side = 'server'"""%(field['full'], field['searge_s']))    

conn.commit()

gc = conn.cursor()
gc.execute("""SELECT m.id, c.name, c.notch
             FROM methods m
             INNER JOIN classes c ON c.id=m.class
             WHERE m.name='<init>'""")
             
conn.commit()
for row in gc:
    c.execute("""UPDATE methods SET name = '%s', notch = '%s', decoded = '%s' WHERE id=%d"""%(row[1].split('/')[-1], row[2], row[1].split('/')[-1], row[0]))

#c.execute("""DELETE FROM methods WHERE name='<clinit>'""")
c.execute("""UPDATE methods SET notchsig = signature WHERE notchsig = -1""")
c.execute("""UPDATE methods SET notch    = name WHERE notch = '-1'""")

conn.commit()

gc.close()
c.close()
#pprint (classes_id[174])
#pprint (methods)
