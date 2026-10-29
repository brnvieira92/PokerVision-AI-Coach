"""Interface desktop; timers cedem controle ao event loop entre decisões dos bots."""
import math
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QRectF, QTimeLine
from PySide6.QtGui import QColor, QPainter, QFont, QFontDatabase
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QHBoxLayout,
    QVBoxLayout, QLabel, QPushButton, QSpinBox, QComboBox, QTextEdit,
    QStackedWidget, QListWidget, QFormLayout, QMessageBox, QSplitter, QSlider, QTextBrowser, QDialog, QDoubleSpinBox, QScrollArea)
from .engine import Table
from .table_view import Felt
from .bots import Bot, observe
from .cards import LABELS, evaluate
from .education import STAGES, cards_text, readable_history, turn_lesson, GLOSSARY
from .storage import Repository
from .coach import snapshot, analyze, DecisionRecord, review_summary
from .coach_panel import CoachPanel
from .review import ReviewPanel
from .training_ui import TrainingPanel, ProgressPanel, RangesPanel
from .equity_ui import EquityPanel
from .study_ui import StudyPanel
from .assistance import capture as capture_assisted
from .assistance_ui import AssistedDialog
from .tournament_ui import TournamentPanel

SUITS = {'c': '♣', 'd': '♦', 'h': '♥', 's': '♠'}




class Window(QMainWindow):
    def __init__(self, db_path='data/pokervision.sqlite3'):
        super().__init__()
        self.setWindowTitle('PokerVision AI Coach • Academia de poker offline')
        self.resize(1320, 850)
        self.repo = Repository(db_path)
        self.table = Table()
        self.hero, self.session = 0, None
        self.training_mode = 0
        self.closing=False
        self.assistance_paused=False
        self.assisted_dialog=None
        self.assisted_analysis=None
        self.hand_assistance={}
        self.hand_decisions = []
        self.coach_panel = CoachPanel(self)
        self.review_panel = ReviewPanel(self)
        self.training_panel = TrainingPanel(self)
        self.progress_panel = ProgressPanel(self)
        self.ranges_panel = RangesPanel(self)
        self.equity_panel = EquityPanel(self)
        self.study_panel = StudyPanel(self)
        self.tournament_panel = TournamentPanel(self)
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
                            ('Analisar mãos', self.history_page()), ('Configurações', self.settings_page()),
                            ('Coach IA', self.coach_panel), ('Revisão visual', self.review_panel),
                            ('Treinamento', self.training_panel), ('Mãos iniciais', self.ranges_panel),
                            ('Meu progresso', self.progress_panel), ('Plano de estudo', self.study_panel),
                            ('Laboratório de equity', self.equity_panel), ('Jogar Sit & Go',self.tournament_panel)]:
            self.pages.addWidget(page)
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, pg=page: self.show_page(pg))
            nav.addWidget(b)
        help_button = QPushButton('Entender os termos')
        help_button.clicked.connect(self.show_glossary)
        nav.addWidget(help_button)
        nav.addStretch()
        info = QLabel('Fichas fictícias\n\nSit & Go disponível\nMTT previsto para próxima fase\n\nFeche este aplicativo antes\nde abrir clientes de poker real.')
        info.setWordWrap(True)
        nav.addWidget(info)
        sidebar=QWidget()
        sidebar.setLayout(nav)
        sidebar_scroll=QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sidebar_scroll.setWidget(sidebar)
        sidebar_scroll.setMinimumWidth(215)
        layout.addWidget(sidebar_scroll,1)
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
                      'Você recebe duas cartas e tenta formar a melhor combinação de cinco cartas.\n\n'
                      'Os botões e o histórico explicam as ações em português.\n'
                      'O painel ao lado da mesa explica o preço de continuar com exemplos.\n'
                      'Em Entender os termos, consulte as etapas, as combinações e as regras básicas.')
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
        side_lay.addWidget(QLabel('ENTENDA ESTA DECISÃO'))
        self.coach = QTextBrowser()
        side_lay.addWidget(self.coach, 2)
        help_button = QPushButton('Entender os termos e as regras')
        help_button.clicked.connect(self.show_glossary)
        side_lay.addWidget(help_button)
        self.ask_button = QPushButton('Pedir explicação desta decisão')
        self.ask_button.clicked.connect(self.ask_current_decision)
        side_lay.addWidget(self.ask_button)
        self.assist_button=QPushButton('Jogo assistido: pausar e estudar equity')
        self.assist_button.clicked.connect(self.begin_assisted)
        side_lay.addWidget(self.assist_button)
        side.setMinimumWidth(340)
        split.addWidget(side)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 1)
        lay.addWidget(split)
        self.status = QLabel()
        lay.addWidget(self.status)
        controls = QHBoxLayout()
        self.action_buttons = {}
        for action, title in [('fold', 'Desistir'), ('check', 'Passar'), ('call', 'Pagar'),
                              ('raise', 'Apostar / Aumentar'), ('all-in', 'Todas as fichas')]:
            b = QPushButton(title)
            b.clicked.connect(lambda checked=False, a=action: self.human_action(a))
            explanations = {
                'fold': 'Desistir (fold): deixa de disputar esta mão. O que já apostou fica no centro.',
                'check': 'Passar (check): continua na mão sem pagar nada agora.',
                'call': 'Pagar (call): coloca apenas as fichas que faltam para acompanhar a aposta.',
                'raise': 'Apostar / Aumentar (bet / raise): escolhe um novo total para esta rodada no campo ao lado.',
                'all-in': 'Todas as fichas (all-in): coloca em jogo todo o seu saldo disponível.'}
            b.setToolTip(explanations[action])
            self.action_buttons[action] = b
            controls.addWidget(b)
        self.amount = QSpinBox()
        self.amount.setRange(1, 100000000)
        self.amount.setPrefix('Total na rodada: ')
        self.amount.setToolTip('Inclui as fichas que você já apostou nesta rodada. Se já colocou 4 e escolhe 10, acrescenta mais 6.')
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
        review = QPushButton('Estudar as decisões desta mão no Coach')
        review.clicked.connect(self.review_saved_hand)
        lay.addWidget(review)
        visual = QPushButton('Rever visualmente esta mão')
        visual.clicked.connect(self.open_visual_review)
        lay.addWidget(visual)
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
        self.rake_input, self.cap_input = QDoubleSpinBox(), QSpinBox()
        self.rake_input.setRange(0, 10)
        self.rake_input.setDecimals(2)
        self.rake_input.setSuffix(' % do pote')
        self.cap_input.setRange(0, 10000)
        form.addRow('Aposta obrigatória menor', self.sb_input)
        form.addRow('Aposta obrigatória maior', self.bb_input)
        form.addRow('Fichas iniciais (vezes a aposta maior)', self.stack_input)
        form.addRow('Seu assento', self.position)
        form.addRow('Modo', self.mode)
        form.addRow('Taxa fictícia da mesa (rake)', self.rake_input)
        form.addRow('Limite da taxa em fichas (0 = desligada)', self.cap_input)
        apply = QPushButton('Aplicar e iniciar nova sessão')
        apply.clicked.connect(self.configure)
        form.addRow(apply)
        rebuy = QPushButton('Repor as fichas de todos até o valor inicial')
        rebuy.clicked.connect(self.rebuy)
        form.addRow(rebuy)
        form.addRow(QLabel('Configuração e recomposição disponíveis somente entre mãos.\n'
                          'O guia funciona sem Ollama. Configure a IA opcional na página Coach IA.'))
        return page

    def show_page(self, page):
        if page is self.tournament_panel and (not self.table.finished or self.assistance_paused or (self.training_mode==1 and self.session is not None)):
            self.error('Termine a mão de Cash Game e finalize a sessão de Avaliação antes de acessar o Sit & Go.')
            return
        if page is self.tournament_panel:
            self.tournament_panel.refresh_saved()
        study_pages=(self.training_panel,self.ranges_panel,self.progress_panel,self.equity_panel,self.study_panel)
        if page in study_pages and not self.can_study():
            self.coach_panel.output.setPlainText('Finalize a sessão de Avaliação para acessar os exercícios, as correções e os conjuntos de mãos.')
            self.pages.setCurrentWidget(self.coach_panel)
            return
        self.refresh_history()
        if page is self.review_panel:
            self.review_panel.reload()
        elif page is self.training_panel:
            self.training_panel.refresh_access()
        elif page is self.ranges_panel:
            self.ranges_panel.refresh_access()
        elif page is self.progress_panel:
            self.progress_panel.reload()
        elif page is self.equity_panel:
            self.equity_panel.refresh_access()
        elif page is self.study_panel:
            self.study_panel.reload()
        self.pages.setCurrentWidget(page)

    def configure(self):
        if self.tournament_panel.active:
            self.error('Conclua ou abandone o Sit & Go antes de iniciar uma sessão de Cash Game.')
            return
        if self.assistance_paused:
            return
        if not self.table.finished:
            self.error('Termine a mão antes de mudar a sessão.')
            return
        try:
            hero = self.position.currentIndex()
            names = ['Atlas', 'Luna', 'Nilo', 'Íris', 'Theo', 'Sol']
            names[hero] = 'Você'
            table = Table(names, [self.stack_input.value()*self.bb_input.value()]*6,
                          self.sb_input.value(), self.bb_input.value(),
                          rake_bps=round(self.rake_input.value()*100), rake_cap=self.cap_input.value())
            if self.session:
                self.repo.close_session(self.session)
            self.table, self.hero = table, hero
            self.training_mode = self.mode.currentIndex()
            self.hand_decisions = []
            self.hand_assistance={}
            self.assisted_analysis=None
            self.coach_panel.clear_context()
            self.review_panel.lock()
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
        if self.tournament_panel.active:
            self.error('Conclua ou abandone o Sit & Go antes de jogar Cash Game.')
            return
        if self.assistance_paused:
            return
        try:
            if self.session is None:
                self.session = self.repo.session(self.settings())
            self.table.start()
            self.hand_decisions = []
            self.hand_assistance={}
            self.assisted_analysis=None
            self.coach_panel.clear_context()
            self.review_panel.lock()
            self.felt.deal.start()
            self.refresh()
        except ValueError as exc:
            self.error(str(exc))

    def human_action(self, action):
        if self.table.actor != self.hero:
            return
        self.perform(action, self.amount.value() if action == 'raise' else None)

    def perform(self, action, amount=None):
        if self.assistance_paused:
            return
        try:
            decision = analyze(snapshot(self.table, self.hero)) if self.table.actor == self.hero else None
            active = self.assisted_analysis or self.coach_panel.active_analysis
            if decision and active and active.decision.model_dump(exclude={'id'}) == decision.decision.model_dump(exclude={'id'}):
                decision = active
            before = len(self.table.board)
            self.table.act(action, amount)
            if decision:
                self.hand_decisions.append(DecisionRecord(analysis=decision, action=action, amount=amount))
                self.assisted_analysis=None
                self.coach_panel.clear_context()
            if len(self.table.board) != before:
                self.felt.deal.start()
            if self.table.finished:
                self.repo.save(self.session, self.table, [r.model_dump() for r in self.hand_decisions],
                               assistance=list(self.hand_assistance.values()))
                if self.training_mode == 0:
                    self.coach_panel.load_review(self.hand_decisions, 'Revisão da última mão concluída')
            self.refresh()
        except (ValueError, OSError) as exc:
            self.error(str(exc))

    def bot_step(self):
        if not self.assistance_paused and not self.table.finished and self.table.actor != self.hero:
            obs = observe(self.table)
            self.perform(*self.bots[self.table.actor].decide(obs))

    def refresh(self):
        t = self.table
        self.felt.update()
        self.log.setPlainText(readable_history(t.history))
        bar = self.log.verticalScrollBar()
        bar.setValue(bar.maximum())
        human = t.actor == self.hero and not t.finished and not self.assistance_paused
        legal = t.legal() if human else {}
        for action, button in self.action_buttons.items():
            allowed = (legal.get('raise_allowed') if action == 'raise' else
                       legal.get('all_in') if action == 'all-in' else legal.get(action))
            button.setEnabled(human and bool(allowed))
        self.action_buttons['call'].setText(f"Pagar {legal.get('call', 0)} fichas")
        self.new_button.setEnabled(t.finished and not self.tournament_panel.active)
        self.ask_button.setEnabled(human and self.training_mode == 0)
        self.assist_button.setEnabled(human and self.training_mode == 0)
        self.amount.setEnabled(human)
        self.slider.setEnabled(human)
        self.coach_panel.update_buttons()
        if self.training_panel.access_allowed != self.can_study():
            self.training_panel.refresh_access()
        self.ranges_panel.refresh_access()
        self.equity_panel.refresh_access()
        if not self.can_study() and self.pages.currentWidget() in (self.training_panel,self.ranges_panel,self.progress_panel,self.equity_panel,self.study_panel):
            self.pages.setCurrentWidget(self.coach_panel)
        if human:
            minimum, maximum = min(legal['minimum'], legal['maximum']), legal['maximum']
            self.slider.setRange(minimum, maximum)
            self.amount.setRange(minimum, maximum)
            self.status.setText(f"Sua vez. Para apostar ou aumentar, escolha o total desta rodada: de {minimum} a {maximum} fichas.")
        else:
            self.status.setText('Mão concluída. Clique em Nova mão.' if t.finished else f'{t.players[t.actor].name} está pensando…')
        if self.assistance_paused:
            self.status.setText('Jogo pausado para estudo. Volte da janela de ajuda para escolher sua ação.')
        elif self.tournament_panel.active:
            self.status.setText('Sit & Go em andamento. Volte a Jogar Sit & Go para continuar; Cash Game fica disponível após encerrar o torneio.')
        if human and self.training_mode == 0:
            self.coach.setPlainText(turn_lesson(t, self.hero))
        elif t.finished and t.number:
            hero_player = t.players[self.hero]
            initial = t.initial_stacks[self.hero]
            difference = hero_player.stack - initial
            self.coach.setPlainText(
                f'Mão encerrada. Suas cartas: {cards_text(hero_player.hole)}.\n\n'
                f'Você começou com {initial} fichas e terminou com {hero_player.stack}. '
                f'Saldo desta mão: {difference:+d} fichas.\n\n'
                'O histórico mostra as ações e quem recebeu as fichas. Receber fichas pode incluir '
                'a devolução do que o próprio jogador apostou; não é sempre lucro.\n\n'
                'Na comparação final, cada jogador usa sua melhor combinação de 5 cartas. '
                'Dois pares de valores diferentes não empatam: o par mais alto vence. '
                'Com pares iguais, comparam-se as outras cartas mais altas.\n\n'
                'Ganhar ou perder uma mão, sozinho, não mostra se a decisão foi boa. '
                'Na próxima mão, observe quanto custa continuar antes de decidir. '
                'Consulte o guia para conhecer a ordem de todas as combinações.')
        elif self.training_mode == 1 and not t.finished:
            self.coach.setPlainText('Modo Avaliação: explicações da decisão ficam ocultas durante a mão. '
                                    'O guia de termos continua disponível para consulta.')
        else:
            self.coach.setPlainText('Clique em Nova mão para receber suas duas cartas. '
                                    'Quando chegar sua vez, explicarei quanto custa continuar e o significado das opções. '
                                    'Você também pode abrir Entender os termos agora.')
        sessions, hands = self.repo.stats()
        self.stats_label.setText(f'{hands} mãos concluídas  ·  {sessions} sessões locais\n'
                                 'Abra Treinamento para praticar e Meu progresso para acompanhar seus acertos por assunto.')

    def refresh_history(self):
        self.saved_hands = self.repo.hands()
        self.history_list.clear()
        for i, session, number, payload in self.saved_hands:
            self.history_list.addItem(('Sit & Go · ' if payload.get('context',{}).get('kind')=='sit_and_go' else '')+f'Mão #{i} · Sessão {session} · Mão {number}')

    def select_history(self, row):
        if row < 0 or row >= len(getattr(self, 'saved_hands', [])):
            return
        payload = self.saved_hands[row][3]
        assisted_note=f"Esta mão teve estudo assistido em {len(payload.get('assistance',[]))} decisões.\n\n" if payload.get('assistance') else ''
        self.history_text.setPlainText(assisted_note+'Cartas da mesa: ' + cards_text(payload['board']) + '\n\n' +
            readable_history(payload['history']) + '\n\nFichas ao terminar:\n' +
            '\n'.join(f"{p['name']}: {p['stack']} fichas | {cards_text(p['hole'])}" for p in payload['players']))

    def can_study(self):
        tournament=getattr(self,'tournament_panel',None)
        if tournament and tournament.evaluation_active:
            return False
        return self.training_mode == 0 or self.session is None

    def open_visual_review(self):
        if not self.can_review():
            self.error('Termine a mão e finalize a sessão de Avaliação antes de revisar.')
            return
        row=self.history_list.currentRow()
        hand_id=self.saved_hands[row][0] if 0<=row<len(getattr(self,'saved_hands',[])) else None
        self.review_panel.reload(hand_id)
        self.pages.setCurrentWidget(self.review_panel)

    def can_review(self):
        if self.tournament_panel.evaluation_active:
            return False
        return self.table.finished and (self.training_mode == 0 or self.session is None)

    def can_explain(self, analysis):
        if self.tournament_panel.evaluation_active:
            return False
        if self.assistance_paused:
            return False
        if self.training_mode == 1:
            return self.table.finished and self.session is None
        if self.table.finished:
            return True
        if self.table.actor != self.hero:
            return False
        return snapshot(self.table, self.hero).model_dump(exclude={'id'}) == analysis.decision.model_dump(exclude={'id'})

    def ask_current_decision(self):
        if self.assistance_paused:
            return
        if self.table.actor != self.hero or self.training_mode != 0:
            return
        analysis = analyze(snapshot(self.table, self.hero))
        self.pages.setCurrentWidget(self.coach_panel)
        self.coach_panel.request_current(analysis)

    def begin_assisted(self):
        if self.assistance_paused or self.training_mode!=0 or self.table.finished or self.table.actor!=self.hero:
            return
        scenario=capture_assisted(self.table,self.hero)
        analysis=analyze(snapshot(self.table,self.hero))
        previous=self.assisted_analysis
        if previous and previous.decision.model_dump(exclude={'id'})==analysis.decision.model_dump(exclude={'id'}):
            analysis=previous
        self.assisted_analysis=analysis
        self.coach_panel.jobs.cancel()
        self.equity_panel.jobs.cancel()
        self.assistance_paused=True
        dialog=AssistedDialog(self,scenario,analysis)
        dialog.setAttribute(Qt.WA_DeleteOnClose,True)
        self.assisted_dialog=dialog
        self.refresh()
        dialog.show()

    def resume_assisted(self):
        self.assistance_paused=False
        self.assisted_dialog=None
        if not self.closing:
            self.refresh()

    def record_assisted(self,scenario,result,decision_id):
        if self.training_mode==0 and self.assistance_paused and result.scenario_id==scenario.id:
            self.hand_assistance[decision_id]=dict(decision_id=decision_id,scenario=scenario.model_dump(mode='json'),
                                                   result=result.model_dump(mode='json'))

    def review_saved_hand(self):
        if not self.can_review():
            self.error('Na Avaliação, finalize a sessão antes de estudar decisões. Durante a mão, continue jogando sem dicas.')
            return
        row = self.history_list.currentRow()
        if 0 <= row < len(getattr(self, 'saved_hands', [])):
            payload = self.saved_hands[row][3]
            self.coach_panel.load_review(payload.get('decisions', []), 'Decisões da mão selecionada no histórico')
            self.pages.setCurrentWidget(self.coach_panel)

    def finish_training_session(self):
        if self.tournament_panel.active:
            return
        if not self.table.finished or self.session is None:
            return
        session = self.session
        records = [record for _, sid, _, payload in reversed(self.repo.hands()) if sid == session
                   for record in payload.get('decisions', [])]
        self.repo.close_session(session)
        self.session = None
        self.coach_panel.load_review(records, 'Sessão finalizada: escolha as decisões para estudar')
        self.pages.setCurrentWidget(self.coach_panel)
        self.refresh()

    def show_glossary(self):
        if not hasattr(self, 'glossary'):
            self.glossary = QDialog(self)
            self.glossary.setWindowTitle('Entender os termos — Guia para começar')
            self.glossary.resize(680, 650)
            layout = QVBoxLayout(self.glossary)
            content = QTextBrowser()
            content.setHtml(GLOSSARY)
            layout.addWidget(content)
            close = QPushButton('Voltar ao jogo')
            close.clicked.connect(self.glossary.hide)
            layout.addWidget(close)
        self.glossary.show()
        self.glossary.raise_()
        self.glossary.activateWindow()

    def error(self, message):
        QMessageBox.warning(self, 'PokerVision', message)

    def closeEvent(self, event):
        pending_sng=self.tournament_panel.active and not self.tournament_panel.table.finished
        if not self.table.finished or pending_sng:
            message=('A mão atual do Sit & Go será descartada. O torneio poderá ser retomado do último intervalo entre mãos. Encerrar?'
                     if pending_sng else 'A mão atual não foi concluída e não será salva. Encerrar?')
            answer = QMessageBox.question(self, 'Encerrar', message)
            if answer != QMessageBox.Yes:
                event.ignore()
                return
        self.closing=True
        self.timer.stop()
        if self.assisted_dialog:
            self.assisted_dialog.shutdown()
        self.tournament_panel.shutdown()
        self.coach_panel.shutdown()
        self.equity_panel.shutdown()
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
        QTextEdit,QTextBrowser,QListWidget { background:#131f2e; border:1px solid #2a3a4d; padding:8px; }
        QLabel { padding:5px; }
        QTabBar::tab { background:#233549; color:#e6edf6; padding:9px; }
        QTabBar::tab:selected { background:#31564d; }
    ''')


def main():
    app = QApplication(sys.argv)
    style_app(app)
    window = Window()
    window.show()
    sys.exit(app.exec())
