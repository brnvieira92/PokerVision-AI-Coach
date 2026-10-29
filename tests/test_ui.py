import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from pokervision.ui import Window, style_app


@pytest.fixture(scope='module')
def app():
    application = QApplication.instance() or QApplication([])
    style_app(application)
    return application


def test_gui_playable_session_and_history(app, tmp_path):
    w = Window(tmp_path/'ui.sqlite3')
    w.timer.stop()
    w.table.seed = 42
    w.show()
    w.pages.setCurrentIndex(1)
    w.new_button.click()
    app.processEvents()
    assert len(w.table.players) == 6
    assert all(len(p.hole) == 2 for p in w.table.players)
    for _ in range(300):
        if w.table.finished:
            break
        if w.table.actor == w.hero:
            legal = w.table.legal()
            action = 'check' if legal['check'] else 'call'
            assert w.action_buttons[action].isEnabled()
            w.action_buttons[action].click()
        else:
            w.bot_step()
        app.processEvents()
    assert w.table.finished
    assert sum(p.stack for p in w.table.players) == 1200
    assert w.repo.stats() == (1,1)
    assert w.new_button.isEnabled()
    w.refresh_history()
    w.history_list.setCurrentRow(0)
    assert 'Entrega das fichas' in w.history_text.toPlainText()
    w.felt.deal.stop()
    w.grab().save('artifacts/mesa-validada.png')
    w.close()


def test_evaluation_hides_tips_and_reconfigure(app, tmp_path):
    w = Window(tmp_path/'eval.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.mode.setCurrentIndex(1)
    w.configure()
    assert w.hero == 3
    w.new_hand()
    assert w.table.actor == 3
    assert 'Modo Avaliação' in w.coach.toPlainText()
    assert 'Entenda o preço' not in w.coach.toPlainText()
    assert w.action_buttons['call'].isEnabled()
    for _ in range(300):
        if w.table.finished:
            break
        l = w.table.legal()
        w.perform('check' if l['check'] else 'call')
    w.close()


def test_beginner_ui_and_glossary_preserve_saved_history(app, tmp_path):
    w = Window(tmp_path/'beginner.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.rake_input.setValue(2.5)
    w.configure()
    assert w.table.rake_bps == 250
    w.new_hand()
    assert 'Pagar 2 fichas' == w.action_buttons['call'].text()
    assert '2 ÷ 5 = 40.0%' in w.coach.toPlainText()
    assert 'aposta obrigatória menor' in w.log.toPlainText()
    assert 'small blind' in w.table.history[0]
    w.show_glossary()
    assert w.glossary.isVisible()
    from PySide6.QtWidgets import QTextBrowser
    content = w.glossary.findChild(QTextBrowser).toPlainText()
    for term in ('equity', 'rake', 'Posição', 'range', 'stack efetivo'):
        assert term in content
    w.glossary.hide()
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    w.close()


def wait_jobs(app, jobs, timeout=3):
    import time
    from PySide6.QtTest import QTest
    deadline=time.monotonic()+timeout
    while jobs.busy and time.monotonic()<deadline:
        app.processEvents()
        QTest.qWait(10)
    app.processEvents()
    assert not jobs.busy


def test_learning_coach_offline_and_decision_persistence(app, tmp_path):
    w=Window(tmp_path/'phase2.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.configure()
    w.new_hand()
    assert w.ask_button.isEnabled()
    w.ask_button.click()
    wait_jobs(app,w.coach_panel.jobs)
    assert 'não é sua chance de ganhar' in w.coach_panel.output.toPlainText()
    assert 'sem LLM' in w.coach_panel.progress.text()
    analysis=w.coach_panel.active_analysis
    assert w.repo.coach_report(analysis.decision.id)
    w.human_action('call')
    assert w.coach_panel.active_analysis is None
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    records=w.repo.hands()[0][3]['decisions']
    assert records and records[0]['analysis']['decision']['board']==[]
    assert records[0]['action']=='call'
    w.finish_training_session()
    assert w.session is None and w.coach_panel.records
    w.close()


def test_evaluation_blocks_coach_until_session_ends(app, tmp_path):
    from pokervision.coach import snapshot,analyze
    w=Window(tmp_path/'evaluation2.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.mode.setCurrentIndex(1)
    w.configure()
    w.new_hand()
    analysis=analyze(snapshot(w.table,w.hero))
    assert not w.ask_button.isEnabled() and not w.can_explain(analysis)
    # Alterar o combo sem aplicar não muda o modo da sessão em andamento.
    w.mode.setCurrentIndex(0)
    w.refresh()
    assert not w.ask_button.isEnabled()
    w.coach_panel.request_current(analysis)
    assert not w.coach_panel.jobs.busy
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    assert not w.can_review() and not w.can_explain(analysis)
    w.finish_training_session()
    assert w.can_review()
    w.coach_panel.explain_button.click()
    wait_jobs(app,w.coach_panel.jobs)
    assert 'preço' in w.coach_panel.output.toPlainText()
    w.close()


def test_worker_keeps_event_loop_responsive_and_serializes(app):
    import threading
    import time
    from PySide6.QtCore import QTimer
    from PySide6.QtTest import QTest
    from pokervision.workers import BackgroundJobs
    main_id=threading.get_ident()
    jobs=BackgroundJobs()
    ticks,results=[],[]
    timer=QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda:ticks.append(1))
    timer.start()
    def slow(token,progress):
        for i in range(12):
            token.check()
            time.sleep(.01)
            progress(i)
        return 'done'
    assert jobs.start(slow,lambda value:results.append((value,threading.get_ident())),lambda msg:None)
    assert not jobs.start(slow,lambda v:None,lambda m:None)
    wait_jobs(app,jobs)
    timer.stop()
    assert len(ticks)>3 and results==[('done',main_id)]
    errors=[]
    assert jobs.start(slow,lambda value:None,errors.append)
    jobs.cancel()
    wait_jobs(app,jobs)
    assert errors and 'cancelada' in errors[0]


def test_download_requires_ui_confirmation(app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    w=Window(tmp_path/'authorize.sqlite3')
    w.timer.stop()
    calls=[]
    monkeypatch.setattr(w.coach_panel.provider,'pull',lambda model,**kwargs:calls.append(kwargs))
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.No)
    w.coach_panel.confirm_pull()
    assert not w.coach_panel.jobs.busy and not calls
    monkeypatch.setattr(QMessageBox,'question',lambda *args:QMessageBox.Yes)
    w.coach_panel.confirm_pull()
    wait_jobs(app,w.coach_panel.jobs)
    assert len(calls)==1 and calls[0]['authorized'] is True
    w.close()


def test_visual_review_never_shows_future_board_and_creates_exercise(app,tmp_path):
    w=Window(tmp_path/'replay.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.configure()
    w.new_hand()
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    final_board=tuple(w.table.board)
    panel=w.review_panel
    panel.reload()
    assert panel.records and panel.canvas.board==()
    assert len(final_board)==5
    assert panel.values.text().startswith('Antes de agir')
    assert panel.previous.isEnabled() is False
    panel.next.click()
    assert panel.index==1 and len(panel.canvas.board)==3
    assert panel.canvas.board==panel.records[1].analysis.decision.board
    panel.previous.click()
    assert panel.index==0 and panel.canvas.board==()
    panel.practice.click()
    assert w.pages.currentWidget() is w.training_panel
    exercise=w.training_panel.exercise
    assert exercise.topic=='price'
    assert exercise.source_decision_id==panel.records[0].analysis.decision.id
    assert not exercise.board
    w.close()


def test_exercise_submit_correction_and_dashboard_persistence(app,tmp_path):
    path=tmp_path/'learning.sqlite3'
    w=Window(path)
    w.timer.stop()
    panel=w.training_panel
    panel.topic.setCurrentIndex(panel.topic.findData('price'))
    panel.new_button.click()
    exercise=panel.exercise
    panel.submit.click()
    assert w.repo.exercise_attempts()==[]
    assert 'Escolha uma resposta' in panel.feedback.toPlainText()
    wrong=next(b for b in panel.group.buttons() if b.property('choice_key')!=exercise.answer)
    wrong.click()
    panel.submit.click()
    assert 'Resposta correta:' in panel.feedback.toPlainText()
    assert 'não sua chance' in panel.feedback.toPlainText()
    assert len(w.repo.exercise_attempts())==1
    assert not panel.submit.isEnabled()
    panel.answer()
    assert len(w.repo.exercise_attempts())==1
    assert '1 exercício respondido' in w.progress_panel.summary.text()
    w.close()
    w=Window(path)
    w.timer.stop()
    assert len(w.repo.exercise_attempts())==1
    assert '1 exercício respondido' in w.progress_panel.summary.text()
    w.close()


def test_evaluation_cannot_access_training_ranges_or_review(app,tmp_path):
    w=Window(tmp_path/'guard3.sqlite3')
    w.timer.stop()
    w.training_panel.new_exercise()
    assert w.training_panel.exercise
    w.position.setCurrentIndex(3)
    w.mode.setCurrentIndex(1)
    w.configure()
    w.new_hand()
    assert w.training_panel.exercise is None
    assert not w.training_panel.submit.isEnabled()
    w.show_page(w.training_panel)
    assert w.pages.currentWidget() is w.coach_panel
    w.show_page(w.ranges_panel)
    assert w.pages.currentWidget() is w.coach_panel
    w.review_panel.reload()
    assert w.review_panel.locked and not w.review_panel.records
    assert w.review_panel.canvas.board==()
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    w.finish_training_session()
    w.show_page(w.training_panel)
    assert w.pages.currentWidget() is w.training_panel
    w.training_panel.new_button.click()
    assert w.training_panel.exercise
    w.close()


def test_ranges_cells_update_real_combo_count(app,tmp_path):
    from pokervision.ranges import combo_count
    w=Window(tmp_path/'ranges3.sqlite3')
    w.timer.stop()
    panel=w.ranges_panel
    panel.preset.setCurrentText('Seu conjunto (clique para editar)')
    assert combo_count(panel.selected)==0
    panel.toggle(0,0)
    assert panel.selected=={'AA'}
    assert '6 das 1326' in panel.summary.text()
    panel.toggle(0,1)
    assert combo_count(panel.selected)==10
    panel.toggle(1,0)
    assert combo_count(panel.selected)==22
    panel.toggle(0,0)
    assert combo_count(panel.selected)==16
    w.close()


def test_equity_lab_worker_results_and_validation(app,tmp_path):
    w=Window(tmp_path/'lab.sqlite3')
    w.timer.stop()
    panel=w.equity_panel
    panel.preset.setCurrentIndex(2)
    panel.samples.setValue(100)
    panel.run.click()
    wait_jobs(app,panel.jobs)
    assert panel.result and panel.result.equity==1
    assert '100 vitórias' in panel.output.toPlainText()
    panel.examples.setCurrentIndex(1)
    assert len(panel.canvas.board)==5 and panel.canvas.villain
    panel.set_card(panel.hole[1],panel.hole[0].currentData())
    panel.invalidate()
    panel.run.click()
    wait_jobs(app,panel.jobs)
    assert panel.result is None and 'duplicadas' in panel.status.text()
    w.close()


def test_study_plan_persists_baselines_and_completion(app,tmp_path):
    from pokervision.training import ExerciseFactory
    path=tmp_path/'plan.sqlite3'
    w=Window(path)
    w.timer.stop()
    panel=w.study_panel
    panel.reload()
    plan_id=panel.plan.id
    topic=panel.plan.tasks[0].topic
    factory=ExerciseFactory(42)
    for _ in range(5):
        exercise=factory.generate(topic)
        w.repo.answer_exercise(exercise,exercise.answer)
    panel.reload()
    assert '1 de 3 blocos' in panel.summary.text()
    panel.start.click()
    assert w.training_panel.exercise.topic==panel.plan.tasks[1].topic
    w.close()
    w=Window(path)
    w.timer.stop()
    w.study_panel.reload()
    assert w.study_panel.plan.id==plan_id
    assert '1 de 3 blocos' in w.study_panel.summary.text()
    w.close()


def test_progress_period_dropdown_changes_comparison(app,tmp_path):
    from datetime import datetime,timedelta,timezone
    from pokervision.training import ExerciseFactory
    w=Window(tmp_path/'period.sqlite3')
    w.timer.stop()
    factory=ExerciseFactory(4)
    for days,hit in [(10,False),(1,True)]:
        exercise=factory.generate('price')
        chosen=exercise.answer if hit else next(c.key for c in exercise.choices if c.key!=exercise.answer)
        w.repo.answer_exercise(exercise,chosen)
        with w.repo.db:
            w.repo.db.execute('UPDATE exercise_attempts SET created=? WHERE exercise_id=?',
                ((datetime.now(timezone.utc)-timedelta(days=days)).isoformat(),exercise.id))
    panel=w.progress_panel
    panel.period.setCurrentIndex(1)
    assert panel.table.item(1,1).text()=='1'
    assert panel.table.item(1,5).text()=='0/1 (0%)'
    assert panel.table.item(1,6).text()=='+100.0'
    w.close()


def test_evaluation_blocks_lab_and_plan(app,tmp_path):
    w=Window(tmp_path/'guard4.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.mode.setCurrentIndex(1)
    w.configure()
    w.new_hand()
    for page in (w.equity_panel,w.study_panel):
        w.show_page(page)
        assert w.pages.currentWidget() is w.coach_panel
    assert not w.equity_panel.run.isEnabled()
    w.study_panel.reload()
    assert not w.study_panel.start.isEnabled()
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    w.finish_training_session()
    w.show_page(w.study_panel)
    assert w.study_panel.start.isEnabled()
    w.close()


def test_review_imports_only_visible_cards_into_simplified_lab(app,tmp_path):
    from pokervision.probability import simulate
    w=Window(tmp_path/'review_lab.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.configure()
    w.new_hand()
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    w.review_panel.reload()
    w.review_panel.explore.click()
    panel=w.equity_panel
    assert panel.mode.currentData()=='random' and not panel.canvas.board
    assert not panel.canvas.villain
    assert 'apenas um' in panel.source_note
    assert not panel.jobs.busy
    old=panel.generation
    panel.invalidate()
    result=simulate(('As','Ks'),('Qs','Js','Ts','2c','3d'),opponent=('Ah','Ad'),samples=2)
    panel.receive(result,old)
    assert panel.result is None
    w.close()


def test_assisted_game_pauses_computes_resumes_and_records(app,tmp_path):
    w=Window(tmp_path/'assisted.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.configure()
    w.new_hand()
    before=[(p.stack,p.bet,p.invested,list(p.hole)) for p in w.table.players],list(w.table.board),list(w.table.history)
    actor=w.table.actor
    w.assist_button.click()
    dialog=w.assisted_dialog
    assert w.assistance_paused and dialog
    assert not w.action_buttons['call'].isEnabled()
    w.bot_step()
    w.perform('fold')
    assert w.table.actor==actor
    dialog.samples.setValue(100)
    dialog.run.click()
    wait_jobs(app,dialog.jobs,timeout=6)
    assert dialog.result and dialog.result.opponents==5
    assert len(dialog.result.pots)==1
    assert dialog.result.eligible_pot==12
    assert dialog.result.scenario_id==dialog.scenario.id
    assert 'não recomenda uma ação ótima' in dialog.output.toPlainText()
    assert before==([(p.stack,p.bet,p.invested,list(p.hole)) for p in w.table.players],list(w.table.board),list(w.table.history))
    dialog.examples.setCurrentIndex(1)
    assert len(dialog.canvas.board)==5 and not dialog.canvas.villain
    assert w.table.board==[]
    decision_id=dialog.analysis.decision.id
    dialog.accept()
    app.processEvents()
    assert not w.assistance_paused and w.table.actor==actor
    assert w.action_buttons['call'].isEnabled()
    w.begin_assisted()
    reopened=w.assisted_dialog
    assert reopened.analysis.decision.id==decision_id
    reopened.samples.setValue(100)
    reopened.start()
    wait_jobs(app,reopened.jobs,timeout=6)
    assert len(w.hand_assistance)==1
    assert w.hand_assistance[decision_id]['scenario']['id']==reopened.scenario.id
    reopened.accept()
    app.processEvents()
    w.human_action('call')
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    payload=w.repo.hands()[0][3]
    assert len(payload['assistance'])==1
    assert payload['assistance'][0]['decision_id']==decision_id
    assert payload['decisions'][0]['analysis']['decision']['id']==decision_id
    w.close()


def test_evaluation_blocks_assistance_entry_points(app,tmp_path):
    w=Window(tmp_path/'no_assistance.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.mode.setCurrentIndex(1)
    w.configure()
    w.new_hand()
    assert not w.assist_button.isEnabled()
    w.begin_assisted()
    assert w.assisted_dialog is None and not w.assistance_paused
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    assert not w.repo.hands()[0][3]['assistance']
    w.close()


def test_close_assisted_dialog_cancels_and_discards_result(app,tmp_path):
    from PySide6.QtTest import QTest
    w=Window(tmp_path/'cancel_assisted.sqlite3')
    w.timer.stop()
    w.position.setCurrentIndex(3)
    w.configure()
    w.new_hand()
    w.begin_assisted()
    dialog=w.assisted_dialog
    dialog.samples.setValue(1000)
    dialog.start()
    token=dialog.jobs.task.token
    dialog.reject()
    assert token.event.is_set()
    assert not w.assistance_paused and w.assisted_dialog is None
    QTest.qWait(80)
    app.processEvents()
    assert not w.hand_assistance
    while not w.table.finished:
        w.perform('check' if w.table.legal()['check'] else 'call')
    w.close()


def finish_sng_hand(panel):
    for _ in range(500):
        if panel.table.finished:
            return
        legal=panel.table.legal()
        panel.perform('check' if legal['check'] else 'call')
    raise AssertionError('Mão de torneio não terminou')


def test_sng_playable_hand_levels_persistence_and_cash_isolation(app,tmp_path):
    w=Window(tmp_path/'sng_gui.sqlite3')
    w.timer.stop()
    panel=w.tournament_panel
    panel.timer.stop()
    panel.stack.setValue(100)
    panel.big.setValue(10)
    panel.hands_level.setValue(1)
    panel.seed_override=2
    panel.start.click()
    assert panel.active and not panel.table.finished
    assert panel.table is not w.table
    assert all(p.stack==200 for p in w.table.players)
    assert not w.new_button.isEnabled()
    while panel.table.actor!=panel.hero:
        panel.perform('check' if panel.table.legal()['check'] else 'call')
    assert panel.actions['call'].isEnabled()
    panel.actions['call'].click()
    finish_sng_hand(panel)
    assert panel.tournament.completed_hands==1
    assert panel.tournament.next_blinds==(10,20)
    assert panel.next.isEnabled()
    assert 'Modelo ICM' in panel.report.toPlainText()
    hands=w.repo.hands()
    assert hands[0][3]['context']['kind']=='sit_and_go'
    assert hands[0][3]['decisions']
    assert w.repo.tournaments()[0]['completed_hands']==1
    panel.abandon()
    assert not panel.active and w.new_button.isEnabled()
    w.close()


def test_sng_resume_between_hands_preserves_progress(app,tmp_path):
    path=tmp_path/'resume_sng.sqlite3'
    w=Window(path)
    w.timer.stop()
    p=w.tournament_panel
    p.timer.stop()
    p.seed_override=2
    p.hands_level.setValue(1)
    p.start_tournament()
    finish_sng_hand(p)
    stacks=[x.stack for x in p.table.players]
    identity=p.tournament.id
    w.close()
    w=Window(path)
    w.timer.stop()
    p=w.tournament_panel
    p.timer.stop()
    p.restore_selected()
    assert p.tournament.id==identity and p.tournament.completed_hands==1
    assert [x.stack for x in p.table.players]==stacks
    assert p.table.finished and p.next.isEnabled()
    assert p.hands_level.value()==1
    assert p.prizes.currentData()==p.tournament.config.payouts
    p.next.click()
    assert p.table.number==2 and p.table.big==40
    finish_sng_hand(p)
    p.abandon()
    w.close()


def test_sng_evaluation_hides_icm_and_study_until_completion(app,tmp_path):
    w=Window(tmp_path/'evaluation_sng.sqlite3')
    w.timer.stop()
    p=w.tournament_panel
    p.timer.stop()
    p.mode.setCurrentIndex(1)
    p.start_tournament()
    assert p.evaluation_active and not w.can_study()
    assert 'Modo Avaliação' in p.lesson.toPlainText()
    w.show_page(w.equity_panel)
    assert w.pages.currentWidget() is w.coach_panel
    finish_sng_hand(p)
    assert 'Modelo ICM entre mãos' not in p.report.toPlainText()
    assert not w.can_review()
    p.abandon()
    assert w.can_study()
    w.close()


def test_complete_sng_gui_saves_champion_and_all_hands(app,tmp_path):
    from fractions import Fraction
    from pokervision.bots import observe
    w=Window(tmp_path/'complete_sng.sqlite3')
    w.timer.stop()
    p=w.tournament_panel
    p.timer.stop()
    p.stack.setValue(100)
    p.big.setValue(10)
    p.hands_level.setValue(1)
    p.seed_override=2
    p.start_tournament()
    for _ in range(10000):
        if not p.active:
            break
        if p.table.finished:
            p.next_hand()
        else:
            seat=p.table.actor
            p.perform(*p.bots[seat].decide_tournament(observe(p.table),p.table.big))
    assert p.tournament.state=='completed'
    assert len(p.tournament.standings())==6
    assert sum(x.stack for x in p.table.players)==600
    assert sum(Fraction(r['prize_numerator'],r['prize_denominator']) for r in p.tournament.standings())==60
    assert len(w.repo.hands())==p.tournament.completed_hands
    assert w.repo.tournaments()[0]['state']=='completed'
    assert p.tabs.currentWidget() is p.report
    assert w.new_button.isEnabled()
    w.close()
