import json
import sqlite3
import threading
import time
from unittest.mock import patch
import pytest
from pydantic import ValidationError
from pokervision.coach import (snapshot, analyze, DecisionAnalysis, DecisionRecord,
    PokerCoachService, review_summary)
from pokervision.engine import Table
from pokervision.ollama import OllamaProvider, OllamaError, MAIN_MODEL, ECONOMY_MODEL
from pokervision.resources import CancelToken, Cancelled, ResourceManager, HardwareProfiler
from pokervision.storage import Repository


@pytest.fixture
def analysis():
    t = Table(seed=2)
    t.start()
    return analyze(snapshot(t, t.actor))


class FakeProvider:
    choose_model = staticmethod(OllamaProvider.choose_model)

    def __init__(self, mode='valid'):
        self.mode, self.calls = mode, []

    def models(self, token):
        if self.mode == 'offline':
            raise OllamaError('Ollama ausente')
        return [] if self.mode == 'missing' else [MAIN_MODEL, ECONOMY_MODEL]

    def chat(self, model, messages, schema, token, progress, cpu):
        token.check()
        self.calls.append((model, cpu, messages))
        if self.mode == 'gpu-error' and not cpu:
            raise OllamaError('CUDA memory exhausted')
        if self.mode == 'bad-json':
            return 'isto não é JSON'
        facts = json.loads(messages[1]['content'])['facts']
        if self.mode == 'wrong-math':
            facts['price_percent'] = 99.0
        if self.mode == 'wrong-id':
            facts['analysis_id'] = 'outra-decisao'
        result = dict(**facts, lesson_ids=['position','price','limits'],
                      uncertainty='informações insuficientes para escolher a melhor jogada')
        if self.mode == 'invented-prose':
            result['explanation'] = 'Você ganha com certeza'
        if self.mode == 'invented-lesson':
            result['lesson_ids'] = ['all-in-is-optimal']
        if self.mode == 'repeat':
            result['lesson_ids'] = ['price', 'price']
        raw = json.dumps(result,ensure_ascii=False)
        if progress:
            progress(raw[:10])
            progress(raw[10:])
        return raw


def test_snapshot_no_hidden_cards_or_future(analysis):
    s = analysis.decision.model_dump()
    assert s['board'] == ()
    assert 'players' not in s and 'awards' not in s and 'winner' not in s
    t = Table(seed=1)
    t.start()
    old = snapshot(t,t.actor)
    while not t.finished:
        t.act('check' if t.legal()['check'] else 'call')
    assert old.board == () and old.street == 'preflop'
    with pytest.raises(ValueError):
        snapshot(t,0)


def test_math_validation_rejects_wrong_threshold(analysis):
    assert analysis.price_percent == 40.0
    d = analysis.model_dump()
    d['price_percent'] = 50
    with pytest.raises(ValidationError):
        DecisionAnalysis.model_validate(d)


@pytest.mark.parametrize('mode', ['offline','missing','bad-json','wrong-math','wrong-id',
                                  'invented-prose','invented-lesson','repeat'])
def test_invalid_llm_falls_back_to_verified_text(analysis, mode):
    p = FakeProvider(mode)
    reply = PokerCoachService(p,ResourceManager(lambda:10)).explain(analysis,mode='balanced')
    assert reply.source == 'deterministic' and reply.reason
    assert '40%' in reply.text and 'não é sua chance' in reply.text
    assert 'Você ganha com certeza' not in reply.text


def test_valid_local_choice_streaming_and_parameters(analysis):
    p = FakeProvider()
    chunks = []
    reply = PokerCoachService(p,ResourceManager(lambda:10)).explain(
        analysis,mode='economy',progress=chunks.append)
    assert reply.source == 'ollama' and reply.model == ECONOMY_MODEL and len(chunks)==2
    assert 'não provam qual ação é a melhor' in reply.text
    sent = p.calls[0][2][1]['content']
    assert 'awards' not in sent and 'winner' not in sent


def test_gpu_error_retries_cpu(analysis):
    p = FakeProvider('gpu-error')
    reply = PokerCoachService(p,ResourceManager(lambda:10)).explain(analysis,mode='balanced')
    assert reply.source == 'ollama'
    assert [cpu for _,cpu,_ in p.calls] == [False,True]


def test_memory_reduction_does_not_load_large_model(analysis):
    p = FakeProvider()
    reply = PokerCoachService(p,ResourceManager(lambda:2)).explain(
        analysis,mode='balanced',model=MAIN_MODEL)
    assert reply.model == ECONOMY_MODEL
    p.calls.clear()
    reply = PokerCoachService(p,ResourceManager(lambda:1)).explain(analysis,mode='balanced')
    assert reply.source == 'deterministic' and not p.calls and 'Pouca memória' in reply.reason


def test_cancel_does_not_publish_fallback(analysis):
    token = CancelToken()
    token.cancel()
    with pytest.raises(Cancelled):
        PokerCoachService(FakeProvider()).explain(analysis,token=token)


def test_resource_lock_serializes_and_cancel_waiter():
    manager, first, second = ResourceManager(), CancelToken(), CancelToken()
    entered = threading.Event()
    errors=[]
    def waiter():
        try:
            with manager.inference(second):
                entered.set()
        except Cancelled:
            errors.append('cancelled')
    with manager.inference(first):
        thread=threading.Thread(target=waiter)
        thread.start()
        second.cancel()
        thread.join(1)
        assert not entered.is_set()
    assert errors == ['cancelled']
    with manager.inference(CancelToken()):
        pass


def test_hardware_without_gpu_is_valid():
    with patch('pokervision.resources.subprocess.run',side_effect=FileNotFoundError):
        result=HardwareProfiler().profile()
    assert result.ram_total_gb > 0 and result.gpus == []
    assert 'CPU' in result.gpu_note


def test_v1_migration_keeps_hands_and_adds_preferences_reports(tmp_path, analysis):
    path=tmp_path/'old.sqlite3'
    db=sqlite3.connect(path)
    db.execute('CREATE TABLE sessions(id INTEGER PRIMARY KEY, started TEXT, ended TEXT, settings TEXT)')
    db.execute('CREATE TABLE hands(id INTEGER PRIMARY KEY, session_id INTEGER, number INTEGER, payload TEXT, UNIQUE(session_id,number))')
    db.execute("INSERT INTO sessions VALUES(1,'old',NULL,'{}')")
    db.execute("INSERT INTO hands VALUES(1,1,1,'{\"board\":[]}')")
    db.execute('PRAGMA user_version=1')
    db.commit()
    db.close()
    repo=Repository(path)
    assert repo.hands()[0][3] == {'board':[]}
    repo.set_preference('ai_mode','off')
    reply=PokerCoachService().explain(analysis)
    repo.save_coach(reply)
    repo.close()
    repo=Repository(path)
    assert repo.preference('ai_mode')=='off'
    assert repo.coach_report(analysis.decision.id)['text']==reply.text
    assert repo.stats()==(1,1)
    repo.close()


def test_review_is_about_decisions_not_winnings(analysis):
    record=DecisionRecord(analysis=analysis,action='call')
    report=review_summary([record])
    assert '1 decisões' in report and 'não dá nota' in report
    assert 'estruturadas' in review_summary([])


def test_only_local_endpoints_and_explicit_download_authorization():
    with pytest.raises(ValueError):
        OllamaProvider('https://external.example')
    with pytest.raises(PermissionError):
        OllamaProvider().pull(MAIN_MODEL)
    assert OllamaProvider.choose_model(['qwen3:1.7b'],'balanced')=='qwen3:1.7b'
    assert OllamaProvider.choose_model([MAIN_MODEL],'economy') is None
