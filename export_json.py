#!/usr/bin/python

import json
import sqlite3

# TODO: read grid12staticdata.http and output those variables into the json

db = sqlite3.connect("grid12-static.db3")

def query(fields, table):
    c = db.cursor()
    fields = fields.split()

    order = ""
    if 'priority' in fields: order = " ORDER BY priority DESC"
        
    sql = "SELECT %s FROM %s %s" % (", ".join(fields), table, order)

    # Ugh, hack: in the record field names *.foobar should be foobar;
    # we needed the scoped version for the sql only.
    for i, f in enumerate(fields):
        f = f.split(".")
        if len(f) == 2: fields[i] = f[1]
            
    for row in c.execute(sql):
        record = {}
        for i, field in enumerate(fields):
            record[field] = row[i]
        yield record
        
    c.close()


def substitute_shape(record):
    "delete record.shapelistid and add record.shape"
    c = db.cursor()
    sql = "SELECT name, priority, color, open, symmetrical, points FROM shape WHERE shapelistid=?"
    record['shape'] = []
    for name, priority, color, open, symmetrical, points in c.execute(sql, [record['shapelistid']]):
        record['shape'].append({'name': name, 'priority': priority, 'color': color,
                                'open': open, 'symmetrical': symmetrical, 'points': points})

    del record['shapelistid']


playertanks = {}  # {tankdefid: record}
for record in query("tankdefid unlocklevel description", "playertank"):
    playertanks[record['tankdefid']] = record


modules = {} # {tankdefid: record}
for record in query("tankdefid code moduleproperty.name bonus",
                    "moduleproperty INNER JOIN playertank USING (playertankid) INNER JOIN tankdef USING (tankdefid)"):
    modules.setdefault(record['tankdefid'], [])
    modules[record['tankdefid']].append(record)

    
enemy = {}  # {tankdefid: record}
for record in query("tankdefid", "enemy"):
    enemy[record['tankdefid']] = record


lootdrop = {}  # {tankdefid: record}
for record in query("tankdefid type quantity chance lootbagcolor",
                    "lootdrop INNER JOIN enemy USING (droplistid) INNER JOIN droplist USING (droplistid)"):
    # NOTE: In the lootdrop table, quantity means quantity for gridshards, prisms, splinters and coins.
    # However, for items (protomods, storage, tanks, augments), quantity is the base level of the item,
    # and quantity is always 1. 50% of item drops are at the base level; 25% are at base level+1; 12.5%
    # are at base level +2, etc. A max of 10 extra levels can be added.
    if record['type'] in ('protomodule', 'storagespace', 'tankunlock', 'augment', 'module'):
        record['level'] = record['quantity']
        record['quantity'] = 1
    else:
        record['level'] = 0

    lootdrop.setdefault(record['tankdefid'], [])
    lootdrop[record['tankdefid']].append(record)

    
fortressdef = {}  # {tankdefid: record}
for record in query("tankdefid difficulty faction powersource maxchildren cooldown", "fortressdef"):
    fortressdef[record['tankdefid']] = record

    
shields = {} # tankdefid -> [record, ...]
for record in query("tankdefid priority maxstrength regenrate regendelay angleleft angleright color",
                    "shielddef"):
    shields.setdefault(record['tankdefid'], [])
    shields[record['tankdefid']].append(record)


triggers = {} # tankdefid = [record, ...]
for record in query("tankdefid priority cooldown",
                    "triggerdef INNER JOIN playertank USING (playertankid)"):
    triggers.setdefault(record['tankdefid'], [])
    triggers[record['tankdefid']].append(record)


guns = {} # turretdefid -> [record, ...]
for record in query("turretdefid name x y gunrange damage cooldown clipsize reloadms lasercolor weapontype shootsound gundef.shapelistid",
                    "turretdef_gundef INNER JOIN gundef USING (gundefid)"):
    substitute_shape(record)
    guns.setdefault(record['turretdefid'], [])
    guns[record['turretdefid']].append(record)


turrets = {} # tankdefid -> [record, ...]
for record in query("tankdefid turretdefid x y f maxdf maxtraverse priority turretdef.shapelistid",
                    "tankdef_turretdef INNER JOIN turretdef USING (turretdefid)"):
    substitute_shape(record)
    turrets.setdefault(record['tankdefid'], [])
    turrets[record['tankdefid']].append(record)
    record['guns'] = guns.get(record['turretdefid'], [])

# TODO: fortressredoubtdef, armadadef

tanks = {} # id -> record
for record in query("tankdefid tankdef.name hitpoints maxspeed maxaccel maxdf maxddf radius flying shapelistid",
                    "tankdef"):
    substitute_shape(record)
    tanks[record['name']] = record
    tankdefid = record['tankdefid']
    record['turrets'] = turrets.get(tankdefid, [])
    if tankdefid in shields: record['shields'] = shields[tankdefid]
    if tankdefid in playertanks: record['playertank'] = playertanks[tankdefid]
    if tankdefid in enemy: record['enemy'] = enemy[tankdefid]
    if tankdefid in fortressdef: record['fortressdef'] = fortressdef[tankdefid]
    if tankdefid in triggers: record['triggers'] = triggers[tankdefid]
    if tankdefid in modules: record['modules'] = modules[tankdefid]
    if tankdefid in lootdrop: record['lootdrop'] = lootdrop[tankdefid]

    
# HTTP headers have timestamp of sql file
headers = open("grid12staticdata.http", 'r').read()

# Write out a readable json file
f = open("grid12-static.js", 'wt')
f.write("var grid12 = {};\n")
f.write("grid12.tanks = ")
json.dump(tanks, f, indent=2)
f.write(";\ngrid12.headers = ")
json.dump(headers, f, indent=2)
f.write(";\n")

# Write out another one that's roughly half the size, by removing spaces
f = open("grid12-static.min.js", 'wt')
f.write("var grid12 = {};\n")
f.write("grid12.tanks = ");
json.dump(tanks, f, separators=(',', ':'))
f.write(";\ngrid12.headers = ")
json.dump(headers, f, separators=(',', ':'))
f.write(";\n")
