"""Mesa Sit & Go independente do Cash Game; checkpoints apenas entre mãos."""
from fractions import Fraction
import sqlite3
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QSpinBox,
    QComboBox,QSplitter,QTextBrowser,QTabWidget,QMessageBox)
from .engine import Table
from .table_view import Felt
from .tournament import Tournament,TournamentConfig,allocate_prizes
from .tournament_bots import TournamentBot
from .bots import observe
from .coach import snapshot,analyze,DecisionRecord
from .education import readable_history,turn_lesson


class TournamentPanel(QWidget):
    table_caption='POKERVISION / SIT & GO'

    def __init__(self,window):
        super().__init__()
        self.window=window
        self.tournament=None
        self.preview=Table()
        self.hero=0
        self.learning=True
        self.auto=False
        self.decisions=[]
        self.persisted_hand=0
        self.seed_override=None
        self.saved=[]
        self.bots=[TournamentBot(p,37+i) for i,p in enumerate(
            ['TAG','LAG','Tight passive','Loose passive','Conservador','TAG'])]
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel('SIT & GO • TORNEIO DE UMA MESA COM 6 JOGADORES'))
        intro=QLabel('Todos começam com as mesmas fichas. Sem recomposição: quem fica sem fichas ao fim de uma mão é eliminado. '
                     'Os blinds sobem por quantidade de mãos. Inscrição e prêmios são pontos fictícios, separados das fichas da mesa.')
        intro.setWordWrap(True)
        lay.addWidget(intro)
        config=QHBoxLayout()
        self.stack=QSpinBox()
        self.stack.setRange(100,100000)
        self.stack.setValue(1000)
        self.stack.setPrefix('Fichas: ')
        self.big=QSpinBox()
        self.big.setRange(2,10000)
        self.big.setValue(20)
        self.big.setPrefix('Aposta maior: ')
        self.hands_level=QSpinBox()
        self.hands_level.setRange(1,50)
        self.hands_level.setValue(5)
        self.hands_level.setPrefix('Mãos/nível: ')
        self.entry=QSpinBox()
        self.entry.setRange(1,10000)
        self.entry.setValue(10)
        self.entry.setPrefix('Inscrição: ')
        self.prizes=QComboBox()
        self.prizes.addItem('2 premiados: 60% / 40%',(60,40))
        self.prizes.addItem('3 premiados: 50% / 30% / 20%',(50,30,20))
        self.mode=QComboBox()
        self.mode.addItems(['Aprendizagem','Avaliação sem dicas'])
        for widget in (self.stack,self.big,self.hands_level,self.entry,self.prizes,self.mode):
            config.addWidget(widget)
        lay.addLayout(config)
        buttons=QHBoxLayout()
        self.start=QPushButton('Iniciar novo torneio')
        self.start.clicked.connect(self.start_tournament)
        self.next=QPushButton('Próxima mão')
        self.next.clicked.connect(self.next_hand)
        self.watch=QPushButton('Simular restante após eliminação')
        self.watch.clicked.connect(self.toggle_auto)
        self.stop=QPushButton('Abandonar entre mãos')
        self.stop.clicked.connect(self.abandon)
        for button in (self.start,self.next,self.watch,self.stop):
            buttons.addWidget(button)
        lay.addLayout(buttons)
        self.status=QLabel()
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        split=QSplitter()
        self.felt=Felt(self)
        split.addWidget(self.felt)
        tabs=QTabWidget()
        self.tabs=tabs
        tabs.setMinimumWidth(340)
        self.log,self.lesson,self.report=QTextBrowser(),QTextBrowser(),QTextBrowser()
        tabs.addTab(self.log,'Mão')
        tabs.addTab(self.lesson,'Aprender')
        tabs.addTab(self.report,'Classificação / ICM')
        split.addWidget(tabs)
        split.setStretchFactor(0,3)
        split.setStretchFactor(1,1)
        lay.addWidget(split,1)
        row=QHBoxLayout()
        self.actions={}
        for key,title in [('fold','Desistir'),('check','Passar'),('call','Pagar'),('raise','Apostar / Aumentar'),('all-in','Todas as fichas')]:
            button=QPushButton(title)
            button.clicked.connect(lambda checked=False,a=key:self.human_action(a))
            row.addWidget(button)
            self.actions[key]=button
        self.amount=QSpinBox()
        self.amount.setRange(1,100000000)
        self.amount.setPrefix('Total na rodada: ')
        row.addWidget(self.amount)
        lay.addLayout(row)
        saved=QHBoxLayout()
        self.saved_choice=QComboBox()
        self.resume=QPushButton('Abrir / retomar torneio salvo')
        self.resume.clicked.connect(self.restore_selected)
        saved.addWidget(self.saved_choice)
        saved.addWidget(self.resume)
        lay.addLayout(saved)
        self.timer=QTimer(self)
        self.timer.setInterval(350)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.refresh_saved()
        self.refresh()

    @property
    def table(self):
        return self.tournament.table if self.tournament else self.preview

    @property
    def active(self):
        return bool(self.tournament and self.tournament.active)

    @property
    def evaluation_active(self):
        return self.active and not self.learning

    def error(self,message):
        QMessageBox.warning(self,'Sit & Go',message)

    def start_tournament(self):
        if self.active:
            self.error('Conclua ou abandone o torneio atual antes de iniciar outro.')
            return
        if not self.window.table.finished or not self.window.can_study():
            self.error('Termine a mão de Cash Game e finalize a sessão de Avaliação antes de abrir um torneio.')
            return
        try:
            payouts=allocate_prizes(6*self.entry.value(),self.prizes.currentData())
            cfg=TournamentConfig(players=6,starting_stack=self.stack.value(),initial_big=self.big.value(),
                                 hands_per_level=self.hands_level.value(),payouts=payouts,seed=self.seed_override)
            tournament=Tournament(cfg)
            tournament.session_id=self.window.repo.session(dict(kind='sit_and_go',hero=0,
                tournament_id=tournament.id,mode=self.mode.currentText(),config=cfg.model_dump(mode='json')))
            self.tournament=tournament
            self.learning=self.mode.currentIndex()==0
            self.auto=False
            self.timer.setInterval(350)
            self.persisted_hand=0
            self.window.coach_panel.clear_context()
            self.window.equity_panel.jobs.cancel()
            self.window.review_panel.lock()
            self.window.repo.set_preference('sng_mode_'+tournament.id,self.learning)
            self.window.repo.save_tournament(tournament)
            self.next_hand()
        except ValueError as exc:
            self.error(str(exc))

    def next_hand(self):
        if not self.active or not self.table.finished:
            return
        try:
            self.decisions=[]
            self.tournament.start_hand()
            self.felt.deal.start()
            self.finish_hand_if_needed()
            self.refresh()
            self.window.refresh()
        except (ValueError,OSError,sqlite3.Error) as exc:
            self.auto=False
            self.error(str(exc))

    def perform(self,action,amount=None):
        if not self.active or self.table.finished:
            return
        try:
            analysis=analyze(snapshot(self.table,self.hero)) if self.table.actor==self.hero else None
            before=len(self.table.board)
            self.tournament.act(action,amount)
            if analysis:
                self.decisions.append(DecisionRecord(analysis=analysis,action=action,amount=amount))
            if len(self.table.board)!=before:
                self.felt.deal.start()
            self.finish_hand_if_needed()
            self.refresh()
        except (ValueError,OSError,sqlite3.Error) as exc:
            self.auto=False
            self.error(str(exc))

    def finish_hand_if_needed(self):
        if self.table.finished and self.table.number>self.persisted_hand:
            self.window.repo.save_tournament_hand(self.tournament,[d.model_dump(mode='json') for d in self.decisions])
            self.persisted_hand=self.table.number
            if not self.tournament.active:
                self.auto=False
                self.timer.setInterval(350)
                self.tabs.setCurrentWidget(self.report)
            self.refresh_saved()
            self.window.refresh()

    def human_action(self,action):
        if self.table.actor==self.hero and self.hero in self.tournament.remaining:
            self.perform(action,self.amount.value() if action=='raise' else None)

    def tick(self):
        if not self.isVisible() or not self.active:
            return
        if self.table.finished:
            if self.auto:
                self.next_hand()
            return
        if self.table.actor!=self.hero:
            self.perform(*self.bots[self.table.actor].decide_tournament(observe(self.table),self.table.big))

    def toggle_auto(self):
        if self.active and self.hero not in self.tournament.remaining:
            self.auto=not self.auto
            self.timer.setInterval(10 if self.auto else 350)
            self.refresh()

    def abandon(self):
        if not self.active or not self.table.finished:
            return
        self.tournament.abandon()
        self.auto=False
        self.window.repo.save_tournament(self.tournament)
        self.refresh_saved()
        self.refresh()
        self.window.refresh()

    def refresh_saved(self):
        selected=self.saved_choice.currentData()
        self.saved=self.window.repo.tournaments()
        self.saved_choice.clear()
        labels={'ready':'Pronto','running':'Em andamento','completed':'Concluído','abandoned':'Abandonado'}
        for data in self.saved:
            self.saved_choice.addItem(f"{labels[data['state']]} • {data['completed_hands']} mãos • {data['id'][:8]}",data['id'])
        index=self.saved_choice.findData(selected)
        if index>=0:
            self.saved_choice.setCurrentIndex(index)

    def restore_selected(self):
        if self.active or not self.window.table.finished or not self.window.can_study():
            self.error('Encerre o jogo atual antes de retomar outro torneio.')
            return
        selected=self.saved_choice.currentData()
        data=next((d for d in self.saved if d['id']==selected),None)
        if not data:
            return
        try:
            restored=Tournament.restore(data)
            if restored.config.players!=6:
                raise ValueError('Esta primeira mesa de torneio suporta seis jogadores na interface.')
            self.tournament=restored
            self.window.coach_panel.clear_context()
            self.window.equity_panel.jobs.cancel()
            self.window.review_panel.lock()
            self.learning=self.window.repo.preference('sng_mode_'+self.tournament.id,True)
            self.mode.setCurrentIndex(0 if self.learning else 1)
            self.stack.setValue(restored.config.starting_stack)
            self.big.setValue(restored.config.initial_big)
            self.hands_level.setValue(restored.config.hands_per_level)
            self.entry.setValue(sum(restored.config.payouts)//restored.config.players)
            prize_index=self.prizes.findData(restored.config.payouts)
            if prize_index<0:
                self.prizes.addItem('Prêmios salvos: '+' / '.join(map(str,restored.config.payouts)),restored.config.payouts)
                prize_index=self.prizes.count()-1
            self.prizes.setCurrentIndex(prize_index)
            self.hero=self.tournament.hero
            self.persisted_hand=self.tournament.completed_hands
            self.decisions=[]
            self.auto=False
            self.timer.setInterval(350)
            self.refresh()
            self.window.refresh()
        except (ValueError,KeyError) as exc:
            self.error('Não foi possível retomar: '+str(exc))

    def refresh(self):
        t=self.table
        active=self.active
        human=active and not t.finished and t.actor==self.hero
        legal=t.legal() if human else {}
        self.felt.update()
        self.log.setPlainText(readable_history(t.history))
        for action,button in self.actions.items():
            allowed=legal.get('raise_allowed') if action=='raise' else legal.get('all_in') if action=='all-in' else legal.get(action)
            button.setEnabled(human and bool(allowed))
        self.actions['call'].setText(f"Pagar {legal.get('call',0)}")
        self.amount.setEnabled(human)
        if human:
            self.amount.setRange(min(legal['minimum'],legal['maximum']),legal['maximum'])
        self.start.setEnabled(not active)
        self.resume.setEnabled(not active)
        self.next.setEnabled(active and t.finished and not self.auto)
        self.watch.setEnabled(active and self.hero not in self.tournament.remaining)
        self.watch.setText('Parar aceleração' if self.auto else 'Simular restante após eliminação')
        self.stop.setEnabled(active and t.finished and not self.auto)
        for widget in (self.stack,self.big,self.hands_level,self.entry,self.prizes,self.mode):
            widget.setEnabled(not active)
        if not self.tournament:
            self.status.setText('Configure o torneio e inicie. Não há dinheiro real, recompra ou taxa nas mãos.')
            self.lesson.setPlainText('Uma inscrição fictícia dá direito a um stack igual ao dos adversários. As fichas não são convertidas diretamente em prêmio; a classificação define o valor fictício recebido.')
            return
        s=self.tournament
        turn='Sua vez' if human else 'Mão concluída' if t.finished else f'{t.players[t.actor].name} está decidindo'
        self.status.setText(f'{len(s.remaining)} de 6 participantes • Mão {t.number} • Blinds {t.small}/{t.big} • {turn}\n'+
                            (f'Próxima mão: nível {s.level}, blinds {s.next_blinds[0]}/{s.next_blinds[1]}. ' if t.finished and active else '')+s.phase)
        if self.learning and human:
            self.lesson.setPlainText(turn_lesson(t,self.hero)+'\n\nTorneio: perder todas as fichas elimina você ao fim da mão. Com dez apostas maiores ou menos, estude a decisão entre colocar tudo ou desistir; não há uma regra universal. Os bots usam uma heurística simples, sem solver ICM.')
        elif not self.learning and active:
            self.lesson.setPlainText('Modo Avaliação: dicas e valores ICM ficam ocultos até o encerramento do torneio. As regras dos botões continuam as mesmas.')
        else:
            self.lesson.setPlainText('O valor das fichas muda conforme os prêmios e os stacks dos demais. Consulte Classificação / ICM entre mãos. O modelo não prevê sua colocação final nem garante prêmio.')
        self.refresh_report()

    def refresh_report(self):
        s=self.tournament
        lines=[f"Situação: {'concluído' if s.state=='completed' else 'abandonado sem classificação final completa' if s.state=='abandoned' else 'em andamento'}",
               'Premiação fictícia: '+', '.join(f'{i+1}º: {v}' for i,v in enumerate(s.config.payouts)),
               '\nClassificação já definida:']
        for row in s.standings():
            place=f"{row['first']}º" if row['first']==row['last'] else f"{row['first']}º–{row['last']}º (empate)"
            value=Fraction(row['prize_numerator'],row['prize_denominator'])
            lines.append(f"{place} • {row['name']} • prêmio fictício {float(value):.2f}")
        if not s.groups:
            lines.append('Nenhuma eliminação ainda.')
        if self.table.finished and (self.learning or not self.active):
            values=s.icm()
            total=sum(self.table.players[i].stack for i in s.remaining)
            remaining_prizes=sum(s.config.payouts[:len(s.remaining)])
            lines.append('\nModelo ICM entre mãos (não é uma previsão):')
            for seat in sorted(s.remaining):
                p=self.table.players[seat]
                proportional=p.stack/total*remaining_prizes
                lines.append(f'{p.name}: {p.stack} fichas • parcela proporcional {proportional:.2f} • valor ICM {values[seat]:.2f}')
            lines.append('\nA parcela proporcional divide o fundo pela quantidade de fichas. O ICM considera as posições premiadas: ter mais fichas não dobra necessariamente o valor esperado de prêmio. Não é uma recomendação de apostar. Ignora habilidade, posição e os próximos blinds.')
        else:
            lines.append('\nICM disponível entre mãos na Aprendizagem, ou ao terminar a Avaliação.')
        lines.append('\nEliminações na mesma mão: quem começou com mais fichas fica melhor colocado. Com stacks iniciais iguais, divide-se a premiação das posições empatadas. Blinds sobem por mãos, não por relógio. Sem antes nesta primeira entrega.')
        self.report.setPlainText('\n'.join(lines))

    def shutdown(self):
        self.timer.stop()
