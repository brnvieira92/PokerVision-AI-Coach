"""Interface desktop; timers cedem controle ao event loop entre decisões dos bots."""
import math
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRectF, QTimeLine
from PySide6.QtGui import QColor, QPainter, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QSpinBox, QComboBox, QTextEdit,
    QStackedWidget, QListWidget, QFormLayout, QMessageBox, QSplitter, QSlider)
from .engine import Table
from .bots import Bot, observe
from .cards import LABELS, evaluate
from .math_engine import pot_odds
from .storage import Repository

SUITS = {'c': '♣', 'd': '♦', 'h': '♥', 's': '♠'}


class Felt(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.deal = QTimeLine(280, self)
        self.deal.valueChanged.connect(lambda _: self.update())
        self.setMinimumSize(620, 440)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QColor('#355b53'))
        p.setBrush(QColor('#123b35'))
        p.drawRoundedRect(QRectF(42, 70, w-84, h-145), 145, 145)
        p.setPen(QColor('#78aa99'))
        p.setFont(QFont('Segoe UI', 11))
        p.drawText(QRectF(0, h/2-55, w, 25), Qt.AlignCenter, 'POKERVISION  /  CASH LAB')
        t = self.window.table
        p.setPen(QColor('#ecdbab'))
        p.drawText(QRectF(0, h/2+40, w, 30), Qt.AlignCenter,
                   f'Pote {t.pot}  ·  {t.street.upper()}  ·  Mão {t.number}')

        def card(x, y, c=None):
            p.setPen(QColor('#364a68' if c is None else '#fff8ec'))
            p.setBrush(QColor('#243554' if c is None else '#fff8ec'))
            p.drawRoundedRect(QRectF(x, y, 39, 54), 5, 5)
            if c:
                p.setPen(QColor('#bf394f' if c[1] in 'dh' else '#142a36'))
                p.setFont(QFont('Segoe UI', 14, QFont.Bold))
                p.drawText(QRectF(x, y, 39, 54), Qt.AlignCenter, c[0]+SUITS[c[1]])
            else:
                p.setPen(QColor('#7d91b7'))
                p.drawText(QRectF(x, y, 39, 54), Qt.AlignCenter, '◆')
        p.setOpacity(self.deal.currentValue() if self.deal.state() == QTimeLine.Running else 1.0)
        for k in range(5):
            c = t.board[k] if k < len(t.board) else None
            card(w/2-111+k*46, h/2-21, c)
        p.setOpacity(1.0)
        for i, player in enumerate(t.players):
            angle = math.pi/2 + i*2*math.pi/len(t.players)
            x, y = w/2+math.cos(angle)*(w/2-100), h/2+math.sin(angle)*(h/2-80)
            p.setPen(QColor('#63e0b0' if t.actor == i else '#3a4a60'))
            p.setBrush(QColor('#19283a'))
            p.drawRoundedRect(QRectF(x-76, y-29, 152, 58), 12, 12)
            p.setFont(QFont('Segoe UI', 10, QFont.Bold))
            p.setPen(QColor('#96a4b6' if player.folded else '#edf4ff'))
            badges = (' D' if i == t.button else '') + (' SB' if i == getattr(t, 'sb', -1) else '') + (' BB' if i == getattr(t, 'bb', -1) else '')
            p.drawText(QRectF(x-74, y-25, 148, 25), Qt.AlignCenter, player.name+badges)
            p.drawText(QRectF(x-74, y, 148, 25), Qt.AlignCenter,
                       f'{player.stack} fichas  ·  aposta {player.bet}')
            cy = y+34
            for k, c in enumerate(player.hole):
                reveal = i == self.window.hero or (t.finished and not player.folded)
                card(x-42+k*45, cy, c if reveal else None)


class Window(QMainWindow):
    def __init__(self, db_path='data/pokervision.sqlite3'):
        super().__init__()
        self.setWindowTitle('PokerVision AI Coach • Academia de poker offline')
        self.resize(1320, 850)
        self.repo = Repository(db_path)
        self.table = Table()
        self.hero, self.session = 0, None
        self.bots = [Bot(profile, i*17) for i, profile in enumerate(
            ['TAG', 'LAG', 'Tight passive', 'Loose passive', 'Conservador', 'TAG'])]
        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        nav = QVBoxLayout()
        brand = QLabel('POKERVISION\nAI COACH\n\nACADEMIA OFFLINE')
        brand.setStyleSheet('font-size:18px; color:#69e6b5; padding:18px')
        nav.addWidget(brand)
        self.pages = QStackedWidget()
        for label, page in [('Início', self.home_page()), ('Jogar Cash Game', self.game_page()),
                            ('Analisar mãos', self.history_page()), ('Configurações', self.settings_page())]:
            self.pages.addWidget(page)
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, pg=page: self.show_page(pg))
            nav.addWidget(b)
        nav.addStretch()
        info = QLabel('Fichas fictícias\n\nSNG • MTT • Coach LLM\nPrevistos para próximas fases\n\nFeche este aplicativo antes\nde abrir clientes de poker real.')
        info.setWordWrap(True)
        nav.addWidget(info)
        layout.addLayout(nav, 1)
        layout.addWidget(self.pages, 5)
        self.timer = QTimer(self)
        self.timer.setInterval(450)
        self.timer.timeout.connect(self.bot_step)
        self.timer.start()
        self.refresh()

    def home_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(QLabel('SEU LABORATÓRIO DE TEXAS HOLD’EM'))
        title = QLabel('Pratique uma decisão de cada vez.')
        title.setStyleSheet('font-size:30px; font-weight:700')
        lay.addWidget(title)
        text = QLabel('Mesa Cash Game 6-max, adversários virtuais e matemática verificável.\n'
                      'Tudo funciona offline, sem contas ou serviços pagos.\n\n'
                      'Comece em Jogar Cash Game. O botão Nova mão distribui as cartas.\n'
                      'O valor de Bet / Raise representa sua aposta total na rodada.\n\n'
                      'O coach desta fase explica pot odds de forma determinística.\n'
                      'Bots heurísticos não representam estratégia GTO.')
        text.setWordWrap(True)
        lay.addWidget(text)
        self.stats_label = QLabel()
        lay.addWidget(self.stats_label)
        lay.addStretch()
        return page

    def game_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        header = QHBoxLayout()
        header.addWidget(QLabel('CASH GAME  /  MESA DE TREINAMENTO'))
        self.new_button = QPushButton('Nova mão')
        self.new_button.clicked.connect(self.new_hand)
        header.addWidget(self.new_button)
        full = QPushButton('Tela cheia')
        full.clicked.connect(lambda: self.showNormal() if self.isFullScreen() else self.showFullScreen())
        header.addWidget(full)
        lay.addLayout(header)
        split = QSplitter()
        self.felt = Felt(self)
        split.addWidget(self.felt)
        side = QWidget()
        side_lay = QVBoxLayout(side)
        side_lay.addWidget(QLabel('HISTÓRICO DA MÃO'))
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        side_lay.addWidget(self.log)
        side_lay.addWidget(QLabel('CONCEITOS E MATEMÁTICA'))
        self.coach = QLabel()
        self.coach.setWordWrap(True)
        side_lay.addWidget(self.coach)
        split.addWidget(side)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        lay.addWidget(split)
        self.status = QLabel()
        lay.addWidget(self.status)
        controls = QHBoxLayout()
        self.action_buttons = {}
        for action, title in [('fold', 'Fold'), ('check', 'Check'), ('call', 'Call'),
                              ('raise', 'Bet / Raise'), ('all-in', 'All-in')]:
            b = QPushButton(title)
            b.clicked.connect(lambda checked=False, a=action: self.human_action(a))
            self.action_buttons[action] = b
            controls.addWidget(b)
        self.amount = QSpinBox()
        self.amount.setRange(1, 100000000)
        self.amount.setPrefix('Total: ')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.amount.setValue)
        self.amount.valueChanged.connect(self.slider.setValue)
        controls.addWidget(self.amount)
        lay.addWidget(self.slider)
        lay.addLayout(controls)
        return page

    def history_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.addWidget(QLabel('MÃOS CONCLUÍDAS  /  HISTÓRICO LOCAL'))
        self.history_list = QListWidget()
        self.history_text = QTextEdit()
        self.history_text.setReadOnly(True)
        self.history_list.currentRowChanged.connect(self.select_history)
        lay.addWidget(self.history_list, 1)
        lay.addWidget(self.history_text, 3)
        return page

    def settings_page(self):
        page = QWidget()
        form = QFormLayout(page)
        self.sb_input, self.bb_input, self.stack_input = QSpinBox(), QSpinBox(), QSpinBox()
        for widget, value in [(self.sb_input, 1), (self.bb_input, 2), (self.stack_input, 100)]:
            widget.setRange(1, 100000)
            widget.setValue(value)
        self.position = QComboBox()
        self.position.addItems([f'Assento {i+1}' for i in range(6)])
        self.mode = QComboBox()
        self.mode.addItems(['Aprendizagem', 'Avaliação (sem dicas durante a mão)'])
        self.rake_input, self.cap_input = QSpinBox(), QSpinBox()
        self.rake_input.setRange(0, 1000)
        self.rake_input.setSuffix(' pontos-base (100 = 1%)')
        self.cap_input.setRange(0, 10000)
        form.addRow('Small blind', self.sb_input)
        form.addRow('Big blind', self.bb_input)
        form.addRow('Stack inicial em BB', self.stack_input)
        form.addRow('Seu assento', self.position)
        form.addRow('Modo', self.mode)
        form.addRow('Rake fictício', self.rake_input)
        form.addRow('Teto do rake em fichas (0 = sem rake)', self.cap_input)
        apply = QPushButton('Aplicar e iniciar nova sessão')
        apply.clicked.connect(self.configure)
        form.addRow(apply)
        rebuy = QPushButton('Recompor todos para o stack inicial')
        rebuy.clicked.connect(self.rebuy)
        form.addRow(rebuy)
        form.addRow(QLabel('Configuração e recomposição disponíveis somente entre mãos.\n'
                          'Fase 1: execução em CPU, sem GPU ou Ollama necessários.'))
        return page

    def show_page(self, page):
        self.refresh_history()
        self.pages.setCurrentWidget(page)

    def configure(self):
        if not self.table.finished:
            self.error('Termine a mão antes de mudar a sessão.')
            return
        try:
            hero = self.position.currentIndex()
            names = ['Atlas', 'Luna', 'Nilo', 'Íris', 'Theo', 'Sol']
            names[hero] = 'Você'
            table = Table(names, [self.stack_input.value()*self.bb_input.value()]*6,
                          self.sb_input.value(), self.bb_input.value(),
                          rake_bps=self.rake_input.value(), rake_cap=self.cap_input.value())
            if self.session:
                self.repo.close_session(self.session)
            self.table, self.hero = table, hero
            self.session = self.repo.session(self.settings())
            self.refresh()
        except ValueError as exc:
            self.error(str(exc))

    def settings(self):
        return dict(small=self.table.small, big=self.table.big, hero=self.hero,
                    stacks=[p.stack for p in self.table.players], mode=self.mode.currentText(),
                    rake_bps=self.table.rake_bps, rake_cap=self.table.rake_cap)

    def rebuy(self):
        if not self.table.finished:
            self.error('Recomponha fichas somente entre mãos.')
            return
        target = self.stack_input.value()*self.table.big
        for i, p in enumerate(self.table.players):
            if p.stack < target:
                self.table.rebuy(i, target-p.stack)
        self.refresh()

    def new_hand(self):
        try:
            if self.session is None:
                self.session = self.repo.session(self.settings())
            self.table.start()
            self.felt.deal.start()
            self.refresh()
        except ValueError as exc:
            self.error(str(exc))

    def human_action(self, action):
        if self.table.actor != self.hero:
            return
        self.perform(action, self.amount.value() if action == 'raise' else None)

    def perform(self, action, amount=None):
        try:
            before = len(self.table.board)
            self.table.act(action, amount)
            if len(self.table.board) != before:
                self.felt.deal.start()
            if self.table.finished:
                self.repo.save(self.session, self.table)
            self.refresh()
        except (ValueError, OSError) as exc:
            self.error(str(exc))

    def bot_step(self):
        if not self.table.finished and self.table.actor != self.hero:
            obs = observe(self.table)
            self.perform(*self.bots[self.table.actor].decide(obs))

    def refresh(self):
        t = self.table
        self.felt.update()
        self.log.setPlainText('\n'.join(t.history))
        bar = self.log.verticalScrollBar()
        bar.setValue(bar.maximum())
        human = t.actor == self.hero and not t.finished
        legal = t.legal() if human else {}
        for action, button in self.action_buttons.items():
            allowed = (legal.get('raise_allowed') if action == 'raise' else
                       legal.get('all_in') if action == 'all-in' else legal.get(action))
            button.setEnabled(human and bool(allowed))
        self.action_buttons['call'].setText(f"Call {legal.get('call', 0)}")
        self.new_button.setEnabled(t.finished)
        if human:
            minimum, maximum = min(legal['minimum'], legal['maximum']), legal['maximum']
            self.slider.setRange(minimum, maximum)
            self.amount.setRange(minimum, maximum)
            self.status.setText(f"Sua vez · mínimo total {legal['minimum']} · máximo {legal['maximum']}")
        else:
            self.status.setText('Mão concluída. Clique em Nova mão.' if t.finished else f'{t.players[t.actor].name} está pensando…')
        if human and self.mode.currentIndex() == 0:
            call = legal['call']
            self.coach.setText(f'Pote atual: {t.pot}. Custo do call: {call}.\n'
                f'Equity de equilíbrio para call: {pot_odds(t.pot, call):.1%}.\n\n'
                'Hipótese: nenhuma aposta futura e sem rake adicional. Isso não estima sua equity '
                'nem prova que call é a melhor ação. Considere posição, ranges e stack efetivo.')
        elif t.finished and t.number:
            self.coach.setText('A distribuição dos potes aparece no histórico. Avalie decisões com as '
                               'informações disponíveis naquele momento, sem usar o resultado para julgá-las.')
        else:
            self.coach.setText('Dicas disponíveis na sua vez em modo Aprendizagem.')
        sessions, hands = self.repo.stats()
        self.stats_label.setText(f'{hands} mãos concluídas  ·  {sessions} sessões locais\n'
                                 'Métricas educacionais avançadas serão adicionadas em fases futuras.')

    def refresh_history(self):
        self.saved_hands = self.repo.hands()
        self.history_list.clear()
        for i, session, number, payload in self.saved_hands:
            self.history_list.addItem(f'Mão #{i} · Sessão {session} · Mão {number}')

    def select_history(self, row):
        if row < 0 or row >= len(getattr(self, 'saved_hands', [])):
            return
        payload = self.saved_hands[row][3]
        self.history_text.setPlainText('Board: ' + ' '.join(payload['board']) + '\n\n' +
            '\n'.join(payload['history']) + '\n\nStacks finais:\n' +
            '\n'.join(f"{p['name']}: {p['stack']} | {' '.join(p['hole'])}" for p in payload['players']))

    def error(self, message):
        QMessageBox.warning(self, 'PokerVision', message)

    def closeEvent(self, event):
        if not self.table.finished:
            answer = QMessageBox.question(self, 'Encerrar', 'A mão atual não foi concluída e não será salva. Encerrar?')
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self.timer.stop()
        if self.session:
            self.repo.close_session(self.session)
        self.repo.close()
        event.accept()


def style_app(app):
    # A plataforma offscreen pode não enumerar fontes do Windows automaticamente.
    font = Path('C:/Windows/Fonts/segoeui.ttf')
    if font.exists():
        QFontDatabase.addApplicationFont(str(font))
    app.setFont(QFont('Segoe UI', 10))
    app.setStyle('Fusion')
    app.setStyleSheet('''
        QWidget { background:#101925; color:#e6edf6; font-family:"Segoe UI"; font-size:13px; }
        QPushButton { background:#233549; border:1px solid #3a5068; padding:12px; border-radius:7px; }
        QPushButton:hover { background:#31536a; }
        QPushButton:disabled { color:#647384; background:#172331; }
        QSpinBox,QComboBox { background:#1c2b3c; padding:9px; border:1px solid #3a5068; }
        QTextEdit,QListWidget { background:#131f2e; border:1px solid #2a3a4d; padding:8px; }
        QLabel { padding:5px; }
    ''')


def main():
    app = QApplication(sys.argv)
    style_app(app)
    window = Window()
    window.show()
    sys.exit(app.exec())
