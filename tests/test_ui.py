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
    assert 'Distribuição:' in w.history_text.toPlainText()
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
    assert 'Equity de equilíbrio' not in w.coach.text()
    assert w.action_buttons['call'].isEnabled()
    for _ in range(300):
        if w.table.finished:
            break
        l = w.table.legal()
        w.perform('check' if l['check'] else 'call')
    w.close()
