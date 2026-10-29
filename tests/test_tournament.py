from fractions import Fraction
import json
import sqlite3
import pytest
from pokervision.tournament import Tournament,TournamentConfig,icm_values,allocate_prizes
from pokervision.tournament_bots import TournamentBot
from pokervision.bots import observe
from pokervision.storage import Repository


def play_hand(tournament,policy='call'):
    for _ in range(500):
        if tournament.table.finished:
            return
        legal=tournament.table.legal()
        tournament.act('check' if legal['check'] else 'call' if policy=='call' else 'fold')
    pytest.fail('Mão não terminou')


def test_blinds_change_between_hands_only_and_no_rebuy():
    t=Tournament(TournamentConfig(starting_stack=100,initial_big=2,hands_per_level=1,seed=3))
    t.start_hand()
    assert t.table.big==2 and t.level==1
    with pytest.raises(ValueError):
        t.start_hand()
    with pytest.raises(ValueError):
        t.checkpoint()
    play_hand(t)
    assert t.completed_hands==1 and t.next_blinds==(2,4)
    assert t.table.big==2
    t.start_hand()
    assert t.table.big==4
    play_hand(t)
    assert sum(p.stack for p in t.table.players)==600 and t.table.rake==0
    with pytest.raises(ValueError):
        t.settle_hand()


def fake_result(t,stacks):
    t.start_hand()
    for p,stack in zip(t.table.players,stacks):
        p.stack=stack
    t.table.street='finished'
    t.table.actor=None
    t.settle_hand()


def test_simultaneous_equal_eliminations_split_occupied_prizes_exactly():
    t=Tournament(TournamentConfig(players=4,starting_stack=100,initial_big=2,payouts=(70,30)))
    fake_result(t,[400,0,0,0])
    assert t.state=='completed'
    rows=t.standings()
    assert rows[0]['first']==1
    assert rows[0]['prize_numerator']==70
    for row in rows[1:]:
        assert (row['first'],row['last'])==(2,4)
        assert Fraction(row['prize_numerator'],row['prize_denominator'])==10
    assert sum(Fraction(r['prize_numerator'],r['prize_denominator']) for r in rows)==100


def test_simultaneous_unequal_eliminations_use_starting_stacks():
    t=Tournament(TournamentConfig(players=4,starting_stack=100,initial_big=2,payouts=(70,30)))
    fake_result(t,[180,120,60,40])
    fake_result(t,[400,0,0,0])
    assert [(r['seat'],r['first']) for r in t.standings()]==[(0,1),(1,2),(2,3),(3,4)]


def test_icm_reference_values_and_sums():
    assert icm_values([50,50],[70,30])==pytest.approx([50,50])
    assert icm_values([90,10],[70,30])==pytest.approx([66,34])
    assert icm_values([10,20,30],[100])==pytest.approx([100/6,100/3,50])
    assert icm_values([100]*3,[50,30,20])==pytest.approx([100/3]*3)
    values=icm_values([100,200,300,400,500,600,700,800,900],[500,300,200])
    assert sum(values)==pytest.approx(1000)
    assert list(values)==sorted(values)
    with pytest.raises(ValueError):
        icm_values([0,100],[100])
    assert sum(allocate_prizes(9,(60,40)))==9
    assert allocate_prizes(9,(60,40))==(5,4)


@pytest.mark.parametrize('count,seed',[(2,1),(6,2),(6,5),(9,3)])
def test_complete_tournaments_conserve_chips_and_award_every_position(count,seed):
    t=Tournament(TournamentConfig(players=count,starting_stack=50,initial_big=10,hands_per_level=1,
                                  payouts=(70,30),seed=seed))
    bots=[TournamentBot('TAG',seed+i) for i in range(count)]
    for _ in range(300):
        if not t.active:
            break
        t.start_hand()
        for action in range(500):
            if t.table.finished:
                break
            i=t.table.actor
            t.act(*bots[i].decide_tournament(observe(t.table),t.table.big))
        assert t.table.finished
        t.assert_integrity()
    assert t.state=='completed' and len(t.remaining)==1
    assert len(t.standings())==count
    assert sum(p.stack for p in t.table.players)==50*count
    assert sum(Fraction(r['prize_numerator'],r['prize_denominator']) for r in t.standings())==100
    restored=Tournament.restore(json.loads(json.dumps(t.checkpoint())))
    assert restored.standings()==t.standings()


def test_checkpoint_restores_next_level_button_and_completed_hands():
    t=Tournament(TournamentConfig(initial_big=2,hands_per_level=1,seed=2))
    t.start_hand()
    play_hand(t)
    checkpoint=json.loads(json.dumps(t.checkpoint()))
    restored=Tournament.restore(checkpoint)
    assert restored.table.button==t.table.button
    assert restored.next_blinds==t.next_blinds
    restored.start_hand()
    assert restored.table.number==2 and restored.table.big==4
    play_hand(restored)
    checkpoint['stacks'][0]+=1
    with pytest.raises(ValueError):
        Tournament.restore(checkpoint)


def test_hand_and_checkpoint_are_an_atomic_transaction(tmp_path):
    repo=Repository(tmp_path/'atomic.sqlite3')
    t=Tournament(TournamentConfig(initial_big=2,seed=3))
    t.session_id=repo.session({'kind':'sit_and_go'})
    repo.save_tournament(t)
    t.start_hand()
    play_hand(t)
    repo.db.execute("CREATE TRIGGER fail_checkpoint BEFORE UPDATE ON tournaments BEGIN SELECT RAISE(ABORT,'checkpoint failed'); END")
    with pytest.raises(sqlite3.IntegrityError):
        repo.save_tournament_hand(t)
    assert repo.hands()==[]
    assert repo.tournaments()[0]['completed_hands']==0
    repo.db.execute('DROP TRIGGER fail_checkpoint')
    repo.save_tournament_hand(t)
    assert len(repo.hands())==1 and repo.tournaments()[0]['completed_hands']==1
    assert repo.hands()[0][3]['context']['kind']=='sit_and_go'
    repo.close()


def test_v3_upgrade_preserves_training_hands_and_preferences(tmp_path):
    from pokervision.training import ExerciseFactory
    path=tmp_path/'v3.sqlite3'
    repo=Repository(path)
    exercise=ExerciseFactory(1).generate('price')
    repo.answer_exercise(exercise,exercise.answer)
    repo.set_preference('study_plan',{'original':True})
    session=repo.session({'kind':'cash'})
    from pokervision.engine import Table
    table=Table(seed=1)
    table.start()
    while not table.finished:
        table.act('check' if table.legal()['check'] else 'call')
    repo.save(session,table)
    with repo.db:
        repo.db.execute('DROP TABLE tournaments')
        repo.db.execute('PRAGMA user_version=3')
    repo.close()
    repo=Repository(path)
    assert repo.stats()==(1,1)
    assert len(repo.exercise_attempts())==1
    assert repo.preference('study_plan')=={'original':True}
    assert repo.tournaments()==[]
    assert repo.db.execute('PRAGMA user_version').fetchone()[0]==4
    repo.close()
