from collections import Counter
from itertools import combinations
import sqlite3
import pytest
from pokervision.cards import DECK,evaluate
from pokervision.ranges import hand_class,combo_count,ALL_CLASSES,matrix_class,PRESETS
from pokervision.training import ExerciseFactory,Exercise,TOPICS,correct,topic_progress,recommend_topic,wilson_interval
from pokervision.storage import Repository


def test_169_classes_cover_exactly_1326_hands():
    counts=Counter(hand_class(pair) for pair in combinations(DECK,2))
    assert len(counts)==169 and sum(counts.values())==1326
    assert set(counts)==ALL_CLASSES
    for key,value in counts.items():
        assert value==combo_count([key])
    assert combo_count(ALL_CLASSES)==1326
    assert combo_count(['AA','AA'])==6
    assert matrix_class(0,1)=='AKs' and matrix_class(1,0)=='AKo'
    for preset in PRESETS.values():
        assert set(preset)<=ALL_CLASSES
    with pytest.raises(ValueError):
        combo_count(['AAs'])


@pytest.mark.parametrize('topic',TOPICS)
def test_generated_exercises_have_valid_answers_and_math(topic):
    factory=ExerciseFactory(42)
    for _ in range(80):
        exercise=factory.generate(topic)
        assert correct(exercise,exercise.answer).correct
        for choice in exercise.choices:
            assert correct(exercise,choice.key).correct==(choice.key==exercise.answer)
        if topic=='combinations':
            a=evaluate(exercise.hole+exercise.board)
            b=evaluate(exercise.villain+exercise.board)
            assert exercise.answer==('a' if a>b else 'b' if b>a else 'tie')
        if topic=='ranges':
            assert exercise.answer==hand_class(exercise.hole)
            assert all(c.label in ALL_CLASSES for c in exercise.choices)


def test_price_reference_and_no_equity_claim():
    exercise=ExerciseFactory(1).price(80,20,'decision-before-action')
    expected=next(c.label for c in exercise.choices if c.key==exercise.answer)
    assert expected=='20%'
    assert '80 + 20 = 100' in correct(exercise,exercise.answer).explanation
    assert 'não sua chance' in correct(exercise,exercise.answer).explanation
    assert exercise.source_decision_id=='decision-before-action'
    with pytest.raises(ValueError):
        ExerciseFactory().price(0,20)
    with pytest.raises(ValueError):
        correct(exercise,'not-an-option')


def test_attempts_preserved_and_first_response_cannot_be_changed(tmp_path):
    path=tmp_path/'training.sqlite3'
    repo=Repository(path)
    exercise=ExerciseFactory(1).generate('price')
    wrong=next(c.key for c in exercise.choices if c.key!=exercise.answer)
    feedback=repo.answer_exercise(exercise,wrong)
    assert not feedback.correct
    repo.answer_exercise(exercise,wrong)
    with pytest.raises(ValueError):
        repo.answer_exercise(exercise,exercise.answer)
    assert len(repo.exercise_attempts())==1
    repo.close()
    repo=Repository(path)
    attempt=repo.exercise_attempts()[0]
    assert attempt['exercise']==exercise.model_dump(mode='json')
    assert not attempt['correct'] and attempt['chosen']==wrong
    repo.close()


def test_v2_migration_keeps_preferences_and_reports(tmp_path):
    path=tmp_path/'v2.sqlite3'
    db=sqlite3.connect(path)
    db.execute('CREATE TABLE preferences (key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    db.execute('CREATE TABLE coach_reports (analysis_id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    db.execute("INSERT INTO preferences VALUES('ai_mode','\"economy\"')")
    db.execute("INSERT INTO coach_reports VALUES('past','{\"text\":\"original\"}')")
    db.execute('PRAGMA user_version=2')
    db.commit()
    db.close()
    repo=Repository(path)
    assert repo.preference('ai_mode')=='economy'
    assert repo.coach_report('past')['text']=='original'
    assert repo.exercise_attempts()==[]
    assert repo.db.execute('PRAGMA user_version').fetchone()[0]==4
    repo.close()


def test_progress_and_recommendation_use_sample_and_recent_answers():
    assert recommend_topic(topic_progress([]))=='combinations'
    rows=[dict(topic='combinations',correct=True)]
    assert recommend_topic(topic_progress(rows))=='price'
    rows=[dict(topic=topic,correct=True) for topic in TOPICS for _ in range(3)]
    rows.extend(dict(topic='actions',correct=False) for _ in range(20))
    progress=topic_progress(rows)
    assert recommend_topic(progress)=='actions'
    assert progress['actions']['total']==23 and progress['actions']['recent_correct']==0
    low,high=wilson_interval(1,1)
    assert low<.3 and high==pytest.approx(1)
    assert wilson_interval(0,0) is None
    assert wilson_interval(50,100)[0]>.4


def test_sorted_wheel_and_invalid_progress_counts():
    from pokervision.training import best_five
    assert [c[0] for c in best_five('As 2c 3d 4h 5s Kc Qc'.split())]==list('A2345')
    for correct_count,total in [(-1,2),(3,2),(0,-1),(1.,2)]:
        with pytest.raises(ValueError):
            wilson_interval(correct_count,total)
