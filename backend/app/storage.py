import json
import sqlite3
from pathlib import Path
from uuid import uuid4
from .models import Profile, Settings


class Storage:
    def __init__(self,path:Path):
        path.parent.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(path,check_same_thread=False)
        self.db.execute('PRAGMA journal_mode=WAL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, run TEXT, data TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS deaths (id TEXT PRIMARY KEY, run TEXT, status TEXT, data TEXT NOT NULL);
        ''')
        if self.get('settings') is None: self.put('settings',Settings().model_dump())
        if self.get('profiles') is None: self.put('profiles',{'default':Profile().model_dump()})
        if self.get('run') is None: self.put('run',str(uuid4()))

    def get(self,key):
        row=self.db.execute('SELECT value FROM config WHERE key=?',(key,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self,key,value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO config VALUES (?,?)',(key,json.dumps(value,ensure_ascii=False)))

    def record(self,ev,nuzlocke=False):
        run=self.get('run')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?)',(ev['id'],run,json.dumps(ev,ensure_ascii=False)))
            if nuzlocke and ev['type']=='POKEMON_FAINTED':
                identity=ev['pokemon']['identity']
                key=run+':'+identity
                self.db.execute('INSERT OR IGNORE INTO deaths VALUES (?,?,?,?)',(key,run,'pending',json.dumps(ev,ensure_ascii=False)))
            self.db.execute('DELETE FROM events WHERE rowid NOT IN (SELECT rowid FROM events ORDER BY rowid DESC LIMIT 5000)')

    def events(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT data FROM events ORDER BY rowid DESC LIMIT 100')]

    def deaths(self):
        return [dict(id=r[0],run=r[1],status=r[2],event=json.loads(r[3])) for r in self.db.execute('SELECT * FROM deaths ORDER BY rowid DESC')]
