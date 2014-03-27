#!/usr/bin/python
"""
Read grid12 static data export in mysqldump format
and write it out as an sqlite3 database

From http://www.redblobgames.com/x/jetbolt/viewer/
Copyright 2013 Red Blob Games <redblobgames@gmail.com>
License: Apache v2.0 <http://www.apache.org/licenses/LICENSE-2.0.html>
"""

import sqlite3
import re

db = sqlite3.connect("grid12-static.db3")
c = db.cursor()

flag_creatingtable = False
command = ""
tables = [];

for line in open("grid12staticdata.sql"):
    if flag_creatingtable:
        if line.startswith(")"):
            flag_creatingtable = False
            command = command.rstrip().rstrip(",") + ")"
            c.execute(command)
        else:
            # sqlite doesn't have unique key the same way
            if line.startswith("  UNIQUE KEY"):
                line = ""
                
            # sqlite doesn't have enum
            m_enum = re.match(r'(.*)enum\s*\(.*\)(.*)', line)
            if m_enum:
                line = m_enum.group(1) + " text " + m_enum.group(2)
                
            line = line.replace(" AUTO_INCREMENT", "")
            command += line
        continue
        
    if line.startswith("DROP TABLE"):
        c.execute(line.rstrip(";"))
        continue

    if line.startswith("CREATE TABLE"):
        command = line
        flag_creatingtable = True

        m_tablename = re.match("CREATE TABLE `(.*)`", line)
        if not m_tablename:
            print 'TABLE NAME NOT PARSED', repr(line)
        tables.append(m_tablename.group(1))
        
        continue

    if line.startswith("--") or line.strip() == "":
        continue
    
    if line.startswith("INSERT INTO"):
        line = line.replace("\\'", "''")  # sql standard escaping is '' not \'
        c.execute(line.rstrip(";"));
        continue


# Convenient view
c.execute("DROP VIEW IF EXISTS tank_gun")
c.execute("""
CREATE VIEW tank_gun
AS SELECT *
   FROM tankdef
   INNER JOIN tankdef_turretdef USING (tankdefid)
   INNER JOIN turretdef USING (turretdefid)
   INNER JOIN turretdef_gundef USING (turretdefid)
   INNER JOIN gundef USING (gundefid)
""")

db.commit()
c.close()
