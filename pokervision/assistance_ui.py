"""Janela de estudo da decisão atual; não recebe cartas privadas dos bots."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog,QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,
    QComboBox,QSpinBox,QTextBrowser,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView,QScrollArea)
from .assistance import capture,project_pots,simulate_assisted
from .coach import snapshot,analyze,lessons
from .education import STAGES
from .equity_ui import OutcomeBars
from .review import CardsCanvas
from .workers import BackgroundJobs


class AssistedDialog(QDialog):
    def __init__(self,window,scenario,analysis):
        super().__init__(window)
        self.window=window
        self.scenario=scenario
        self.analysis=analysis
        self.active=True
        self.result=None
        self.jobs=BackgroundJobs(self)
        self.jobs.busy_changed.connect(self.update_controls)
        self.setWindowTitle('Jogo assistido • decisão pausada para estudar')
        self.setWindowModality(Qt.WindowModal)
        self.resize(1050,820)
        outer=QVBoxLayout(self)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        content=QWidget()
        lay=QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        title=QLabel(f'MÃO {scenario.hand} • {STAGES[scenario.street]} • JOGO PAUSADO')
        title.setWordWrap(True)
        lay.addWidget(title)
        intro=QLabel('Estude antes de decidir. Não lemos as cartas privadas dos adversários nem as cartas que ainda sairão do baralho real do simulador. '
                     'Todos os sorteios abaixo são possibilidades independentes. Feche esta janela para voltar à mesma decisão.')
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.canvas=CardsCanvas()
        lay.addWidget(self.canvas)
        self.canvas.set_cards(scenario.hole,scenario.board)
        self.values=QLabel(f'Há {sum(p.invested for p in scenario.players)} fichas no centro. '
            f'Para acompanhar agora: {scenario.call} fichas. Seu saldo: {scenario.players[scenario.hero].stack}. '
            f'Adversários ainda na mão: {sum(not p.folded for i,p in enumerate(scenario.players) if i!=scenario.hero)}.')
        self.values.setWordWrap(True)
        lay.addWidget(self.values)
        assumption=QLabel('HIPÓTESE DE ESTUDO: você paga o preço atual (ou passa se não há custo); '
                         'todos os adversários que continuam pagam o que falta até esse preço, limitados às fichas que têm; '
                         'ninguém aumenta, desiste ou aposta nas próximas rodadas. As cartas restantes são abertas até o fim. '
                         'Isso não prevê o comportamento dos bots nem prova qual é a melhor ação.')
        assumption.setWordWrap(True)
        lay.addWidget(assumption)
        row=QHBoxLayout()
        self.model=QComboBox()
        self.model.addItem('Mãos aleatórias para todos os adversários',None)
        self.model.addItem('Mesmo conjunto de Mãos iniciais para todos','range')
        self.samples=QSpinBox()
        self.samples.setRange(100,1000)
        self.samples.setSingleStep(100)
        self.samples.setValue(300)
        self.samples.setPrefix('Sorteios: ')
        self.run=QPushButton('Calcular esta hipótese')
        self.run.clicked.connect(self.start)
        self.cancel=QPushButton('Cancelar cálculo')
        self.cancel.clicked.connect(self.jobs.cancel)
        for widget in (self.model,self.samples,self.run,self.cancel):
            row.addWidget(widget)
        lay.addLayout(row)
        self.status=QLabel('O cálculo só começa quando você pedir. O jogo continuará pausado até voltar à mesa.')
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.bars=OutcomeBars()
        self.bars.equity_label='Equity contra todos'
        lay.addWidget(self.bars)
        self.pots=QTableWidget(0,4)
        self.pots.setHorizontalHeaderLabels(['Parte das fichas','Fichas líquidas','Você disputa?','Média [faixa de 95%]'])
        self.pots.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.pots.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.pots.setMinimumHeight(150)
        self.pots.setMaximumHeight(230)
        lay.addWidget(self.pots)
        self.examples=QComboBox()
        self.examples.addItem('Cartas conhecidas na decisão atual')
        self.examples.currentIndexChanged.connect(self.show_example)
        lay.addWidget(self.examples)
        self.output=QTextBrowser()
        self.output.setMinimumHeight(200)
        self.output.setPlainText(lessons(analysis)['price']+'\n\n'+lessons(analysis)['options']+'\n\n'+
            'Quando houver potes separados, o cálculo avaliará cada um só entre os participantes elegíveis. '
            'A participação contra todos não é automaticamente a participação em cada pote.')
        lay.addWidget(self.output)
        self.resume=QPushButton('Concluir estudo e voltar à mesma decisão')
        self.resume.clicked.connect(self.accept)
        outer.addWidget(self.resume)
        self.model.currentIndexChanged.connect(self.clear_result)
        self.samples.valueChanged.connect(self.clear_result)
        self.show_pots()
        self.update_controls()

    def still_current(self):
        if not self.active or self.window.closing or self.window.training_mode!=0 or not self.window.assistance_paused:
            return False
        try:
            current=capture(self.window.table,self.window.hero)
            return current.model_dump(exclude={'id'})==self.scenario.model_dump(exclude={'id'})
        except ValueError:
            return False

    def update_controls(self,*_):
        allowed=self.still_current()
        busy=self.jobs.busy
        self.run.setEnabled(allowed and not busy)
        self.model.setEnabled(allowed and not busy)
        self.samples.setEnabled(allowed and not busy)
        self.cancel.setEnabled(busy)
        self.examples.setEnabled(allowed and not busy)

    def clear_result(self,*_):
        self.result=None
        self.bars.result=None
        self.bars.update()
        self.examples.blockSignals(True)
        self.examples.clear()
        self.examples.addItem('Cartas conhecidas na decisão atual')
        self.examples.blockSignals(False)
        self.canvas.set_cards(self.scenario.hole,self.scenario.board)
        self.output.setPlainText('Hipótese alterada. Peça um novo cálculo. Não é possível comparar ações sem supor como os adversários responderiam a cada uma.')
        self.show_pots()

    def show_pots(self,result=None):
        projections=[p.projection for p in result.pots] if result else list(project_pots(self.scenario)[1])
        self.pots.setRowCount(len(projections))
        for i,p in enumerate(projections):
            refund=p.refund_to is not None
            title='Devolução não coberta' if refund else 'Pote principal' if i==0 else f'Pote separado {i}'
            eligible=p.refund_to==self.scenario.hero if refund else self.scenario.hero in p.eligible
            cells=[title,str(p.net),'Devolução para você' if refund and eligible else 'Outra pessoa' if refund else 'Sim' if eligible else 'Não',
                   f'{result.pots[i].hero_average:.1f} [{result.pots[i].interval[0]:.1f} a {result.pots[i].interval[1]:.1f}]' if result else 'Aguardando cálculo']
            for col,text in enumerate(cells):
                self.pots.setItem(i,col,QTableWidgetItem(text))

    def start(self):
        if not self.still_current() or self.jobs.busy:
            return
        classes=tuple(self.window.ranges_panel.selected) if self.model.currentData()=='range' else None
        samples=self.samples.value()
        self.clear_result()
        self.output.setPlainText('Simulando apenas a hipótese declarada. Não mudamos a mão jogável nem consultamos cartas dos bots.')
        if self.jobs.start(lambda token,progress:simulate_assisted(self.scenario,classes=classes,samples=samples,
                           token=token,progress=progress),self.receive,self.failed,self.progress):
            self.status.setText('Calculando em segundo plano. Você pode cancelar ou voltar à mesa.')

    def progress(self,counts):
        if self.active:
            self.status.setText(f'{counts[0]} de {counts[1]} possibilidades. Jogo pausado para estudo.')

    def failed(self,message):
        if self.active:
            self.status.setText(message)

    def receive(self,result):
        if not self.still_current() or result.scenario_id!=self.scenario.id or (self.jobs.task and self.jobs.task.token.event.is_set()):
            return
        self.result=result
        self.bars.result=result
        self.bars.update()
        self.show_pots(result)
        self.examples.blockSignals(True)
        self.examples.clear()
        self.examples.addItem('Cartas conhecidas na decisão atual')
        for i,example in enumerate(result.examples):
            self.examples.addItem(f'Possibilidade {i+1}: {example.outcome}')
        self.examples.blockSignals(False)
        current_pot=sum(p.invested for p in self.scenario.players)
        others_extra=sum(result.final_contributions)-current_pot-self.scenario.call
        fee=sum(p.projection.gross-p.projection.net for p in result.pots)
        price_explanation=(f'Preço para continuar agora: {self.scenario.call} fichas. '
            f'Na hipótese calculada: {current_pot} já no centro + {self.scenario.call} do seu pagamento '
            f'+ {others_extra} dos pagamentos dos demais = {sum(result.final_contributions)} fichas brutas. '
            f'A taxa fictícia retira {fee}. As devoluções aparecem separadas. '
            'Esses totais incluem pagamentos hipotéticos dos outros, não somente o pote que já estava na mesa.')
        text=(f'{result.samples} sorteios contra {result.opponents} adversários. '
              f'Equity de comparação contra todos: {result.equity:.1%}. '
              'Em cada sorteio, uma vitória vale 1; empate entre três vale 1/3, entre quatro vale 1/4, e assim por diante.\n\n'
              f'Faixa conservadora de amostragem (95%): {result.interval[0]:.1%} a {result.interval[1]:.1%}. '
              'Essa faixa não mede a incerteza das hipóteses sobre as mãos e as ações dos adversários.\n\n'
              f'Na hipótese declarada, você disputa {result.eligible_pot} fichas líquidas nos potes indicados. '
              f'Recebimento médio total: {result.expected_award:.2f} fichas; inclui {result.refund} de devolução não coberta. '
              'Receber fichas não é lucro: parte delas pode ser o que você mesmo colocou.\n\n'
              'Potes separados são comparados somente entre seus participantes. A soma dos recebimentos médios por pote '
              'pode diferir da equity contra todos multiplicada pelo pote total, especialmente com stacks diferentes. '
              'As faixas na tabela mostram erro de amostragem por pote; não incluem incerteza sobre a hipótese de comportamento. '
              'Empates distribuem fichas inteiras; sobra vai primeiro à esquerda do botão, como no simulador.\n\n'+
              result.range_description+'\n\n'
              'O cálculo já desconta a taxa fictícia configurada sob a hipótese de abrir o flop e terminar em comparação final. '
              'Não mede o valor de aumentar, não estima chance de fazer os outros desistirem e não recomenda uma ação ótima. '
              'Use o preço e as opções abaixo para entender a decisão, sem tratar os sorteios como cartas futuras reais.\n\n'+
              price_explanation+'\n\n'+lessons(self.analysis)['options'])
        self.output.setPlainText(text)
        self.window.record_assisted(self.scenario,result,self.analysis.decision.id)
        self.status.setText('Cálculo concluído. Estude os potes e as possibilidades; depois volte à mesa para escolher sua ação.')

    def show_example(self,index):
        if index>0 and self.result and index<=len(self.result.examples):
            example=self.result.examples[index-1]
            # Apenas board hipotético; nem cartas reais nem mãos sorteadas dos adversários são exibidas.
            self.canvas.set_cards(self.scenario.hole,example.board)
        else:
            self.canvas.set_cards(self.scenario.hole,self.scenario.board)

    def done(self,result):
        self.active=False
        self.jobs.cancel()
        self.window.resume_assisted()
        super().done(result)

    def shutdown(self):
        self.active=False
        self.jobs.cancel()
