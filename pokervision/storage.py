"""Persistência transacional, migração versionada e histórico reabrível."""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class Repository:
    def __init__(self, path='data/pokervision.sqlite3'):
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        version = self.db.execute('PRAGMA user_version').fetchone()[0]
        if version > 1:
            raise RuntimeError('Banco criado por versão mais recente')
        with self.db:
            self.db.execute('CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, started TEXT NOT NULL, ended TEXT, settings TEXT NOT NULL)')
            self.db.execute('CREATE TABLE IF NOT EXISTS hands (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id), number INTEGER NOT NULL, payload TEXT NOT NULL, UNIQUE(session_id, number))')
            self.db.execute('PRAGMA user_version=1')
        self.db.execute('PRAGMA foreign_keys=ON')

    def session(self, settings):
        with self.db:
            return self.db.execute('INSERT INTO sessions(started,settings) VALUES (?,?)',
                (datetime.now(timezone.utc).isoformat(), json.dumps(settings))).lastrowid

    def save(self, session, table):
        if not table.finished:
            raise ValueError('Somente mãos terminadas')
        payload = dict(board=table.board, button=table.button, history=table.history,
                       players=[dict(name=p.name, hole=p.hole, stack=p.stack,
                                     invested=p.invested, folded=p.folded) for p in table.players],
                       initial_stacks=table.initial_stacks, awards=table.awards,
                       pots=table.pots, rake=table.rake)
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO hands(session_id,number,payload) VALUES (?,?,?)',
                            (session, table.number, json.dumps(payload, ensure_ascii=False)))

    def hands(self):
        return [(i, s, n, json.loads(p)) for i, s, n, p in self.db.execute(
            'SELECT id,session_id,number,payload FROM hands ORDER BY id DESC')]

    def stats(self):
        return self.db.execute('SELECT (SELECT count(*) FROM sessions), (SELECT count(*) FROM hands)').fetchone()

    def close_session(self, session):
        with self.db:
            self.db.execute('UPDATE sessions SET ended=? WHERE id=?', (datetime.now(timezone.utc).isoformat(), session))

    def close(self):
        self.db.close()
