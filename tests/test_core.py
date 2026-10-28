import random
import pytest
from pokervision.cards import DECK, deck, evaluate
from pokervision.engine import Table
from pokervision.bots import Bot, observe
from pokervision.math_engine import pot_odds, spr, call_ev, estimate_equity
from pokervision.storage import Repository


def play_out(t):
    for _ in range(300):
        if t.finished:
            return
        l = t.legal()
        t.act('check' if l['check'] else 'call')
    pytest.fail('Mão não terminou')


def test_deck():
    assert len(DECK) == len(set(DECK)) == 52
    assert deck(42) == deck(42)
    assert deck(42) != deck(43)


@pytest.mark.parametrize('cards,category', [
    ('As Ks Qs Js Ts 2c 3d', 8), ('Ah Ac Ad As Ks 2c 3d', 7),
    ('Ah Ac Ad Ks Kc 2c 3d', 6), ('Ah Jh 9h 5h 3h 2c 3d', 5),
    ('Ah 2c 3d 4s 5h 9c Td', 4), ('Ah Ac Ad Ks Qc 2c 3d', 3),
    ('Ah Ac Kd Ks Qc 2c 3d', 2), ('Ah Ac Kd Qs Jc 2c 3d', 1),
    ('Ah Tc 8d 6s 4c 2c 3d', 0)])
def test_ranking(cards, category):
    assert evaluate(cards.split())[0] == category


def test_tiebreaks_and_validation():
    assert evaluate('As Ac Kd Qh Js'.split()) > evaluate('Ah Ad Kc Qs Tc'.split())
    assert evaluate('As 2c 3h 4d 5s'.split()) < evaluate('2s 3c 4h 5d 6s'.split())
    assert evaluate('As Ks Qs Js Ts 2c 3d'.split()) == evaluate('As Ks Qs Js Ts 4c 5d'.split())
    with pytest.raises(ValueError):
        evaluate(['As']*5)


def test_order_and_blinds():
    t = Table(seed=1)
    t.start()
    assert (t.button, t.sb, t.bb, t.actor) == (0, 1, 2, 3)
    for _ in range(6):
        t.act('check' if t.legal()['check'] else 'call')
    assert t.street == 'flop' and t.actor == 1
    play_out(t)
    t.start()
    assert (t.button, t.sb, t.bb, t.actor) == (1, 2, 3, 4)


def test_heads_up_and_dead_seats():
    t = Table(['A','B','C'], [100, 0, 100], seed=2)
    t.start()
    assert (t.button,t.sb,t.bb,t.actor) == (0,0,2,0)
    t.act('call')
    t.act('check')
    assert t.street == 'flop' and t.actor == 2
    play_out(t)
    t.start()
    assert t.button == 2


def test_illegal_actions_atomic():
    t = Table(seed=4)
    t.start()
    state = [(p.stack,p.bet) for p in t.players]
    for action, value in [('check',None), ('raise',3), ('raise',9999), ('raise',4.5)]:
        with pytest.raises(ValueError):
            t.act(action,value)
        assert state == [(p.stack,p.bet) for p in t.players]
    t.act('raise',6)
    assert t.legal()['minimum'] == 10


def test_short_allin_does_not_reopen():
    t = Table(['A','B','C'], [100,100,13], seed=3)
    t.start()  # A bouton, B SB, C BB
    t.act('raise',10)
    t.act('call')
    t.act('all-in')
    assert t.current == 13 and t.increment == 8
    assert t.actor == 0 and not t.legal()['raise_allowed']
    with pytest.raises(ValueError):
        t.act('all-in')
    t.act('call')
    assert not t.legal()['raise_allowed']
    play_out(t)


def test_cumulative_short_raises_reopen():
    t = Table(['A','B','C','D'], [13,18,100,100], seed=3)
    t.start()  # D first
    t.act('raise',10)
    t.act('all-in')  # A 13
    t.act('all-in')  # B 18
    t.act('call')  # C
    assert t.actor == 3 and t.legal()['raise_allowed']
    assert t.legal()['minimum'] == 26
    play_out(t)


def test_side_pots_and_uncalled_return():
    t = Table(['A','B','C'], [100,20,50], seed=5)
    t.start()
    t.act('all-in')
    t.act('call')
    t.act('call')
    assert t.finished and len(t.board) == 5
    assert [p['amount'] for p in t.pots] == [60,60,50]
    assert t.awards.get(0,0) >= 50
    assert sum(p.stack for p in t.players) == 170


def test_split_and_odd_chip():
    t = Table(['A','B','C'], [10]*3, seed=6)
    t.start()
    # Todos contribuem; C abandona. Board assegura empate de A e B.
    t.players[0].hole = ['2c','3c']
    t.players[1].hole = ['4c','5c']
    t.players[2].hole = ['6c','7c']
    t.board = ['As','Ks','Qs','Js','Ts']
    for p in t.players:
        p.stack, p.invested, p.bet = 7,3,3
    t.players[2].folded = True
    t._settle()
    assert t.awards == {1:5, 0:4}  # odd chip à esquerda do dealer
    assert sum(p.stack for p in t.players) == 30


def test_fold_award_and_rebuy():
    t = Table(seed=9)
    t.start()
    while not t.finished:
        t.act('fold')
    assert sum(p.stack for p in t.players) == 1200
    t.rebuy(0,50)
    assert sum(p.stack for p in t.players) == 1250
    t.start()
    with pytest.raises(ValueError):
        t.rebuy(0,10)


def test_rake_no_flop_no_drop():
    t = Table(['A','B'], [100,100], rake_bps=1000, rake_cap=5)
    t.start()
    t.act('fold')
    assert t.rake == 0
    t.start()
    t.act('all-in')
    t.act('call')
    assert t.rake == 5
    assert sum(p.stack for p in t.players) == 195


def test_equity_and_math():
    assert pot_odds(100,25) == .2
    assert spr(200,20) == 10
    assert call_ev(.2,100,25) == 0
    a = estimate_equity(['As','Ks'], ['Qs','Js','Ts'], samples=30, seed=2)
    assert a.equity == 1 and a.standard_error == 0
    assert a == estimate_equity(['As','Ks'], ['Qs','Js','Ts'], samples=30, seed=2)
    with pytest.raises(ValueError):
        estimate_equity(['As','As'])


def test_storage_migration_reopen(tmp_path):
    path = tmp_path/'test.sqlite3'
    repo = Repository(path)
    session = repo.session({'mode':'test'})
    t = Table(seed=1)
    t.start()
    with pytest.raises(ValueError):
        repo.save(session,t)
    play_out(t)
    repo.save(session,t)
    repo.save(session,t)
    repo.close_session(session)
    repo.close()
    repo = Repository(path)
    assert repo.stats() == (1,1)
    assert repo.hands()[0][3]['board'] == t.board
    assert repo.db.execute('PRAGMA user_version').fetchone()[0] == 1
    repo.close()


def test_observation_has_no_opponent_holes():
    t = Table(seed=1)
    t.start()
    o = observe(t)
    assert o.hole == tuple(t.players[t.actor].hole)
    assert not hasattr(o,'players')


@pytest.mark.parametrize('seed', range(20))
def test_simulated_sessions_conserve_chips(seed):
    rng = random.Random(seed)
    t = Table(seed=seed, stacks=[rng.randrange(2,100) for _ in range(6)])
    bots = [Bot(p, seed+i) for i,p in enumerate(['TAG','LAG','Tight passive','Loose passive','Recreativo','Conservador'])]
    total = sum(p.stack for p in t.players)
    for _ in range(15):
        if sum(p.stack > 0 for p in t.players) < 2:
            break
        t.start()
        for action_count in range(400):
            if t.finished:
                break
            t.act(*bots[t.actor].decide(observe(t)))
        assert t.finished
        assert sum(p.stack for p in t.players) == total
        t.assert_integrity()
