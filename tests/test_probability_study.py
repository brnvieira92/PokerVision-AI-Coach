from datetime import datetime,timedelta,timezone
import pytest
from pokervision.probability import simulate,expand_range
from pokervision.resources import CancelToken,Cancelled
from pokervision.ranges import hand_class
from pokervision.study import make_plan,plan_status,compare_periods
from pokervision.training import TOPICS


def test_known_royal_flush_and_exact_split_reference():
    result=simulate(('As','Ks'),('Qs','Js','Ts','2c','3d'),opponent=('Ah','Ad'),samples=20)
    assert result.wins==20 and result.equity==1 and result.improved_category==0
    assert result.interval[0]<1  # Sem falsa certeza por amostra degenerada.
    split=simulate(('2c','3d'),('As','Ks','Qs','Js','Ts'),opponent=('4c','5d'),samples=20)
    assert split.ties==20 and split.equity==.5


def test_range_expansion_removes_blockers_and_weights_physical_combinations():
    assert len(expand_range({'AA','AKs','AKo'}))==6+4+12
    assert len(expand_range({'AKs'},('As','Ks')))==3
    assert len(expand_range({'AKs'},('As','Ks','Ah')))==2
    result=simulate(('As','Ks'),('2c','3d','4h'),classes={'AKs'},samples=50)
    for example in result.examples:
        assert hand_class(example.opponent)=='AKs'
        known=('As','Ks')+example.opponent+example.board
        assert len(set(known))==len(known)


def test_improvement_is_not_equity_and_seed_reproduces_draws():
    kwargs=dict(opponent=('Kc','Kd'),samples=300,seed=42)
    a=simulate(('8c','8d'),('Kh','7s','2h'),**kwargs)
    b=simulate(('8c','8d'),('Kh','7s','2h'),**kwargs)
    assert a==b
    assert a.wins+a.ties+a.losses==300
    assert a.improved_category>0
    assert any(e.improved and e.outcome=='Derrota' for e in a.examples)
    assert a.improved_category/a.samples!=a.equity
    assert 0<=a.interval[0]<=a.equity<=a.interval[1]<=1


@pytest.mark.parametrize('hole,board,kwargs',[
    (('As','As'),(),{}), (('As','Ks'),('2c',),{}),
    (('As','Ks'),(),{'opponent':('As','Kh')}),
    (('As','Ks'),(),{'classes':set()}),
    (('As','Ks'),(),{'samples':0}),
    (('As','Ks'),(),{'classes':{'AA'},'opponent':('Qh','Qd')}),
])
def test_invalid_simulations_are_rejected(hole,board,kwargs):
    with pytest.raises(ValueError):
        simulate(hole,board,**kwargs)


def test_simulation_cancelled_between_batches():
    token=CancelToken()
    calls=[]
    def progress(counts):
        calls.append(counts)
        token.cancel()
    with pytest.raises(Cancelled):
        simulate(('As','Ks'),('2c','3d','4h'),samples=200,token=token,progress=progress)
    assert calls==[(50,200)]


def test_study_plan_goals_count_only_new_answers():
    attempts=[dict(topic='combinations',correct=True) for _ in range(8)]
    plan=make_plan(attempts)
    assert len(plan.tasks)==3
    assert plan.tasks[0].topic=='price'
    assert all(row['completed']==0 for row in plan_status(plan,attempts))
    later=attempts+[dict(topic='price',correct=False) for _ in range(7)]
    row=next(r for r in plan_status(plan,later) if r['topic']=='price')
    assert row['completed']==row['goal']==5


def test_period_boundaries_have_no_overlap_and_keep_topic_totals():
    now=datetime(2026,10,28,12,tzinfo=timezone.utc)
    def attempt(days,correct):
        return dict(topic='price',correct=correct,created=(now-timedelta(days=days)).isoformat())
    rows=[attempt(0,True),attempt(7,True),attempt(8,False),attempt(14,False),attempt(15,True),attempt(-1,True)]
    result=compare_periods(rows,7,now)
    assert len(result['current'])==2 and len(result['previous'])==2
    assert result['changes']['price']==100
    assert result['changes']['combinations'] is None
    assert len(compare_periods(rows,None,now)['current'])==5
