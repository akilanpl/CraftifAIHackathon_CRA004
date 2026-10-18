import json
import sqlite3
import threading
from pathlib import Path


class Database:
    def __init__(self,path,jsonl_path=None):
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.conn = sqlite3.connect(str(path),check_same_thread=False)
        self.lock = threading.RLock()
        self.jsonl_path = jsonl_path
        self.conn.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS zones (id TEXT PRIMARY KEY, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS incidents (id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS native_events (key TEXT PRIMARY KEY);
        ''')
        self.conn.commit()

    def zones(self):
        with self.lock:
            return [json.loads(r[0]) for r in self.conn.execute('SELECT data FROM zones ORDER BY rowid')]

    def save_zone(self,zone):
        with self.lock,self.conn:
            self.conn.execute('INSERT OR REPLACE INTO zones VALUES (?,?)',(zone['id'],json.dumps(zone)))

    def delete_zone(self,id):
        with self.lock,self.conn:
            self.conn.execute('DELETE FROM zones WHERE id=?',(id,))

    def incidents(self):
        with self.lock:
            return [json.loads(r[0]) for r in self.conn.execute('SELECT data FROM incidents ORDER BY timestamp DESC,rowid DESC')]

    def save_incident(self,event):
        with self.lock,self.conn:
            self.conn.execute('INSERT OR REPLACE INTO incidents VALUES (?,?,?)',(event['id'],event['timestamp'],json.dumps(event)))
        if self.jsonl_path:
            Path(self.jsonl_path).parent.mkdir(parents=True,exist_ok=True)
            with open(self.jsonl_path,'a',encoding='utf-8') as f:
                f.write(json.dumps(event)+'\n')

    def claim_native(self,key):
        with self.lock,self.conn:
            return self.conn.execute('INSERT OR IGNORE INTO native_events VALUES (?)',(key,)).rowcount == 1
