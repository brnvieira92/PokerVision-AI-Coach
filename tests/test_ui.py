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
