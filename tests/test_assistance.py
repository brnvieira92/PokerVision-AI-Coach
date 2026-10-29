import pytest
from pokervision.assistance import (AssistedScenario,PublicPlayer,capture,project_pots,
                                    simulate_assisted,award_for_hero)
from pokervision.engine import Table
from pokervision.cards import evaluate
from pokervision.resources import CancelToken,Cancelled

ROYAL=('As','Ks','Qs','Js','Ts')


def tied_scenario(count=6):
    return AssistedScenario(hand=1,street='river',hero=0,button=0,hole=('2c','3d'),board=ROYAL,
        current_bet=2,call=0,rake_bps=0,rake_cap=0,
        players=tuple(PublicPlayer(name=str(i),stack=98,bet=2,invested=2,folded=False) for i in range(count)))


def test_multiway_tie_is_one_sixth_not_one_half():
    result=simulate_assisted(tied_scenario(),samples=20)
    assert result.opponents==5 and result.ties==20
    assert result.equity==pytest.approx(1/6)
    assert result.expected_award==2
    assert result.eligible_pot==12
    assert sum(result.final_contributions)==12


@pytest.mark.parametrize('rake_bps,cap,expected',[(0,0,50),(1000,10,46)])
def test_short_call_sidepots_and_refund_match_actual_engine(rake_bps,cap,expected):
    t=Table(['A','B','Você'],[100,20,50],seed=4,rake_bps=rake_bps,rake_cap=cap)
    t.start()
    t.act('all-in')
    t.act('call')
    assert t.actor==2 and t.legal()['call']==48
    for p,hole in zip(t.players,[['2c','3c'],['4c','5c'],['6c','7c']]):
        p.hole=hole
    t.board=list(ROYAL)
    t.street='river'
    scenario=capture(t,2)
    result=simulate_assisted(scenario,samples=20)
    assert result.final_contributions==(100,20,50)
    assert len(result.pots)==3
    assert result.pots[2].projection.refund_to==0
    assert result.pots[2].hero_average==0
    assert result.equity==pytest.approx(1/3)
    assert result.expected_award==expected
    t.act('call')
    assert t.finished
    assert t.players[2].stack==result.expected_award
    assert [p['amount'] for p in t.pots]==[p.projection.net for p in result.pots]


def test_folded_contributions_count_but_folded_players_cannot_win():
    s=AssistedScenario(hand=1,street='river',hero=0,button=3,hole=('2c','3d'),board=ROYAL,
        current_bet=0,call=0,rake_bps=0,rake_cap=0,players=(
            PublicPlayer(name='Você',stack=10,bet=0,invested=20,folded=False),
            PublicPlayer(name='B',stack=0,bet=0,invested=20,folded=False),
            PublicPlayer(name='C',stack=0,bet=0,invested=30,folded=True),
            PublicPlayer(name='D',stack=0,bet=0,invested=30,folded=False)))
    r=simulate_assisted(s,samples=20)
    assert r.opponents==2 and r.eligible_pot==80
    assert r.pots[0].projection.eligible==(0,1,3)
    assert r.pots[1].projection.eligible==(3,)
    assert r.expected_award==27  # 80 dividido por 3; primeira sobra à esquerda do botão.
    scores={0:(8,14),1:(8,14),3:(8,14)}
    for pot in r.pots:
        assert sum(award_for_hero(pot.projection,scores,i,3,4) for i in range(4))==pot.projection.net


def test_hypothesis_models_opponents_matching_current_price():
    t=Table(seed=3)
    t.start()
    s=capture(t,t.actor)
    amounts,pots=project_pots(s)
    assert amounts==(2,2,2,2,2,2)
    assert sum(p.gross for p in pots)==12
    assert sum(p.invested for p in s.players)==3


def test_capture_and_results_do_not_depend_on_hidden_hands_or_real_deck():
    t=Table(seed=1)
    t.start()
    hero=t.actor
    a=capture(t,hero)
    for i,p in enumerate(t.players):
        if i!=hero:
            p.hole=['XX','XX']
    t.cards.reverse()
    b=capture(t,hero)
    assert a.model_dump(exclude={'id'})==b.model_dump(exclude={'id'})
    assert all('hole' not in p.model_dump() for p in a.players)
    r1=simulate_assisted(a,samples=30,seed=2)
    r2=simulate_assisted(b,samples=30,seed=2)
    assert r1.model_dump(exclude={'scenario_id'})==r2.model_dump(exclude={'scenario_id'})
    assert all('opponent' not in ex.model_dump() for ex in r1.examples)


def test_impossible_joint_range_and_cancellation_are_handled():
    with pytest.raises(ValueError,match='estreito demais'):
        simulate_assisted(tied_scenario(),classes={'AA'},samples=20)
    token=CancelToken()
    token.cancel()
    with pytest.raises(Cancelled):
        simulate_assisted(tied_scenario(),token=token,samples=20)


def test_joint_range_sampling_does_not_reuse_aces_between_two_opponents():
    s=tied_scenario(3).model_copy(update={'board':('Ks','Qh','Jd','Tc','9s')})
    result=simulate_assisted(s,classes={'AA'},samples=40,seed=7)
    # Cada adversário tem dois dos quatro ases restantes; ambos fazem sequência até o Ás.
    assert result.opponents==2 and result.losses==40 and result.expected_award==0
