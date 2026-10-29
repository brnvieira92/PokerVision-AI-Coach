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
        if version > 4:
            raise RuntimeError('Banco criado por versão mais recente')
        with self.db:
            self.db.execute('CREATE TABLE IF NOT EXISTS sessions (id INTEGER PRIMARY KEY, started TEXT NOT NULL, ended TEXT, settings TEXT NOT NULL)')
            self.db.execute('CREATE TABLE IF NOT EXISTS hands (id INTEGER PRIMARY KEY, session_id INTEGER NOT NULL REFERENCES sessions(id), number INTEGER NOT NULL, payload TEXT NOT NULL, UNIQUE(session_id, number))')
            self.db.execute('CREATE TABLE IF NOT EXISTS coach_reports (analysis_id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
            self.db.execute('CREATE TABLE IF NOT EXISTS preferences (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
            self.db.execute('CREATE TABLE IF NOT EXISTS exercise_attempts (exercise_id TEXT PRIMARY KEY, created TEXT NOT NULL, topic TEXT NOT NULL, exercise TEXT NOT NULL, chosen TEXT NOT NULL, correct INTEGER NOT NULL CHECK(correct IN (0,1)))')
            self.db.execute('CREATE TABLE IF NOT EXISTS tournaments (id TEXT PRIMARY KEY, created TEXT NOT NULL, updated TEXT NOT NULL, state TEXT NOT NULL, payload TEXT NOT NULL)')
            self.db.execute('PRAGMA user_version=4')
        self.db.execute('PRAGMA foreign_keys=ON')

    def session(self, settings):
        with self.db:
            return self.db.execute('INSERT INTO sessions(started,settings) VALUES (?,?)',
                (datetime.now(timezone.utc).isoformat(), json.dumps(settings))).lastrowid

    def _save_hand(self, session, table, decisions=None, assistance=None, context=None, strict=False):
        if not table.finished:
            raise ValueError('Somente mãos terminadas')
        payload = dict(board=table.board, button=table.button, history=table.history,
                       players=[dict(name=p.name, hole=p.hole, stack=p.stack,
                                     invested=p.invested, folded=p.folded) for p in table.players],
                       initial_stacks=table.initial_stacks, awards=table.awards,
                       pots=table.pots, rake=table.rake, decisions=decisions or [], assistance=assistance or [], context=context or {})
        command='INSERT' if strict else 'INSERT OR IGNORE'
        self.db.execute(command+' INTO hands(session_id,number,payload) VALUES (?,?,?)',
                        (session, table.number, json.dumps(payload, ensure_ascii=False)))

    def save(self, session, table, decisions=None, assistance=None, context=None):
        with self.db:
            self._save_hand(session,table,decisions,assistance,context)

    def _write_tournament(self, payload):
        now=datetime.now(timezone.utc).isoformat()
        self.db.execute('INSERT INTO tournaments(id,created,updated,state,payload) VALUES (?,?,?,?,?) '
                        'ON CONFLICT(id) DO UPDATE SET updated=excluded.updated,state=excluded.state,payload=excluded.payload',
                        (payload['id'],now,now,payload['state'],json.dumps(payload,ensure_ascii=False)))

    def save_tournament(self, tournament):
        with self.db:
            self._write_tournament(tournament.checkpoint())
            if not tournament.active and tournament.session_id is not None:
                self.db.execute('UPDATE sessions SET ended=? WHERE id=?',
                                (datetime.now(timezone.utc).isoformat(),tournament.session_id))

    def save_tournament_hand(self,tournament,decisions=None):
        payload=tournament.checkpoint()
        if tournament.session_id is None:
            raise ValueError('Torneio sem sessão persistente')
        with self.db:
            self._save_hand(tournament.session_id,tournament.table,decisions,context=dict(
                kind='sit_and_go',tournament_id=tournament.id,hero=tournament.hero,
                small=tournament.table.small,big=tournament.table.big),strict=True)
            self._write_tournament(payload)
            if not tournament.active:
                self.db.execute('UPDATE sessions SET ended=? WHERE id=?',
                                (datetime.now(timezone.utc).isoformat(),tournament.session_id))

    def tournaments(self):
        return [json.loads(row[0]) for row in self.db.execute('SELECT payload FROM tournaments ORDER BY rowid DESC')]

    def hands(self):
        return [(i, s, n, json.loads(p)) for i, s, n, p in self.db.execute(
            'SELECT id,session_id,number,payload FROM hands ORDER BY id DESC')]

    def stats(self):
        return self.db.execute('SELECT (SELECT count(*) FROM sessions), (SELECT count(*) FROM hands)').fetchone()

    def set_preference(self, key, value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO preferences(key,value) VALUES (?,?)',
                            (key, json.dumps(value, ensure_ascii=False)))

    def preference(self, key, default=None):
        row = self.db.execute('SELECT value FROM preferences WHERE key=?', (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def save_coach(self, reply):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO coach_reports(analysis_id,payload) VALUES (?,?)',
                            (reply.analysis_id, reply.model_dump_json()))

    def coach_report(self, analysis_id):
        row = self.db.execute('SELECT payload FROM coach_reports WHERE analysis_id=?', (analysis_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def answer_exercise(self, exercise, chosen):
        from .training import correct, Exercise
        feedback = correct(exercise, chosen)
        with self.db:
            cursor = self.db.execute(
                'INSERT OR IGNORE INTO exercise_attempts(exercise_id,created,topic,exercise,chosen,correct) VALUES (?,?,?,?,?,?)',
                (exercise.id, datetime.now(timezone.utc).isoformat(), exercise.topic,
                 exercise.model_dump_json(), chosen, int(feedback.correct)))
            if not cursor.rowcount:
                row = self.db.execute('SELECT exercise,chosen FROM exercise_attempts WHERE exercise_id=?', (exercise.id,)).fetchone()
                if chosen != row[1]:
                    raise ValueError('Este exercício já foi respondido. Gere outro para tentar novamente.')
                feedback = correct(Exercise.model_validate_json(row[0]), row[1])
        return feedback

    def exercise_attempts(self):
        return [dict(id=key, created=created, topic=topic, exercise=json.loads(exercise),
                     chosen=chosen, correct=bool(correct))
                for key,created,topic,exercise,chosen,correct in self.db.execute(
                    'SELECT exercise_id,created,topic,exercise,chosen,correct FROM exercise_attempts ORDER BY rowid')]

    def close_session(self, session):
        with self.db:
            self.db.execute('UPDATE sessions SET ended=? WHERE id=?', (datetime.now(timezone.utc).isoformat(), session))

    def close(self):
        self.db.close()
