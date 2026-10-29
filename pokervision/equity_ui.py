"""Laboratório probabilístico independente, em worker e sem dependência do LLM."""
from PySide6.QtCore import Qt,QRectF
from PySide6.QtGui import QPainter,QColor,QFont
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLabel,QPushButton,
    QComboBox,QSpinBox,QTextBrowser,QScrollArea)
from .cards import DECK
from .education import card_name,cards_text
from .probability import simulate
from .review import CardsCanvas
from .workers import BackgroundJobs

PRESETS={
    'Quatro copas contra uma trinca':(('Ah','Kh'),('Qh','Jh','2c'),('Qs','Qd')),
    'Um par contra uma trinca maior':(('8c','8d'),('Kh','7s','2h'),('Kc','Kd')),
    'Comparação com a mesa completa':(('As','Ks'),('Qs','Js','Ts','2c','3d'),('Ah','Ad')),
}


class OutcomeBars(QWidget):
    def __init__(self):
        super().__init__()
        self.result=None
        self.equity_label='Equity: parte média do pote'
        self.setMinimumHeight(150)

    def paintEvent(self,event):
        p=QPainter(self)
        p.setFont(QFont('Segoe UI',10))
        if not self.result:
            p.setPen(QColor('#a6b7ca'))
            p.drawText(self.rect(),Qt.AlignCenter,'Os resultados aparecerão depois da simulação.')
            return
        r=self.result
        rows=[('Vitórias',r.wins/r.samples,'#50bd98'),('Empates',r.ties/r.samples,'#c7ac58'),
              ('Derrotas',r.losses/r.samples,'#c2707d'),(self.equity_label,r.equity,'#669cde')]
        if r.improved_category is not None:
            rows.append(('Categoria superior',r.improved_category/r.samples,'#a68bd1'))
        for i,(label,value,color) in enumerate(rows):
            y=i*29
            p.setPen(QColor('#e6edf6'))
            p.drawText(QRectF(4,y,260,26),Qt.AlignVCenter,label)
            width=max(20,self.width()-350)
            p.fillRect(QRectF(265,y+5,width,16),QColor('#233549'))
            p.fillRect(QRectF(265,y+5,width*value,16),QColor(color))
            p.drawText(QRectF(270+width,y,75,26),Qt.AlignVCenter,f'{value:.1%}')


class EquityPanel(QWidget):
    def __init__(self,window):
        super().__init__()
        self.window=window
        self.jobs=BackgroundJobs(self)
        self.jobs.busy_changed.connect(self.refresh_access)
        self.result=None
        self.hole_used=()
        self.closing=False
        self.generation=0
        self.source_note=''
        self.inputs=[]
        outer=QVBoxLayout(self)
        scroll=QScrollArea()
        scroll.setWidgetResizable(True)
        content=QWidget()
        lay=QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        lay.addWidget(QLabel('LABORATÓRIO DE EQUITY • GANHAR, EMPATAR E MELHORAR SÃO COISAS DIFERENTES'))
        intro=QLabel('Equity é a parte média do pote que você receberia ao comparar as mãos no fim. '
                     'Contra um adversário, uma vitória conta como um pote inteiro e um empate como meio pote. '
                     'A simulação não decide se apostar ou pagar é a melhor ação.')
        intro.setWordWrap(True)
        lay.addWidget(intro)
        form=QFormLayout()
        self.preset=QComboBox()
        self.preset.addItems(PRESETS)
        self.mode=QComboBox()
        for title,value in [('Mão específica, informada abaixo','fixed'),('Mãos aleatórias restantes','random'),
                            ('Conjunto escolhido em Mãos iniciais','range')]:
            self.mode.addItem(title,value)
        form.addRow('Exemplo',self.preset)
        form.addRow('Um adversário com',self.mode)
        def card_combo(optional=False):
            combo=QComboBox()
            if optional:
                combo.addItem('Ainda não aberta',None)
            for code in DECK:
                combo.addItem(card_name(code),code)
            combo.currentIndexChanged.connect(self.invalidate)
            self.inputs.append(combo)
            return combo
        def card_row(count,optional=False):
            row=QWidget()
            line=QHBoxLayout(row)
            line.setContentsMargins(0,0,0,0)
            boxes=[card_combo(optional) for _ in range(count)]
            for box in boxes:
                line.addWidget(box)
            return row,boxes
        own,self.hole=card_row(2)
        board,self.board=card_row(5,True)
        villain,self.villain=card_row(2)
        form.addRow('Suas cartas',own)
        form.addRow('Cartas da mesa, na ordem',board)
        form.addRow('Cartas do adversário específico',villain)
        self.samples=QSpinBox()
        self.samples.setRange(100,2000)
        self.samples.setSingleStep(100)
        self.samples.setValue(600)
        self.seed=QSpinBox()
        self.seed.setRange(0,999999)
        self.seed.setValue(42)
        self.seed.setToolTip('A mesma semente e as mesmas cartas repetem os sorteios para você poder comparar exemplos.')
        form.addRow('Quantidade de simulações',self.samples)
        form.addRow('Semente para repetir o exemplo',self.seed)
        lay.addLayout(form)
        controls=QHBoxLayout()
        self.run=QPushButton('Simular cartas restantes')
        self.run.clicked.connect(self.start)
        self.cancel=QPushButton('Cancelar cálculo')
        self.cancel.clicked.connect(self.jobs.cancel)
        controls.addWidget(self.run)
        controls.addWidget(self.cancel)
        lay.addLayout(controls)
        self.status=QLabel('Escolha um exemplo e clique em Simular. São hipóteses de treino, não cartas conhecidas de uma partida.')
        self.status.setWordWrap(True)
        lay.addWidget(self.status)
        self.canvas=CardsCanvas()
        lay.addWidget(self.canvas)
        self.examples=QComboBox()
        self.examples.addItem('Cartas iniciais deste exemplo')
        self.examples.currentIndexChanged.connect(self.show_example)
        lay.addWidget(self.examples)
        self.bars=OutcomeBars()
        lay.addWidget(self.bars)
        self.output=QTextBrowser()
        self.output.setMinimumHeight(210)
        lay.addWidget(self.output)
        self.inputs.extend([self.preset,self.mode,self.samples,self.seed])
        self.preset.currentIndexChanged.connect(self.apply_preset)
        self.mode.currentIndexChanged.connect(self.invalidate)
        self.samples.valueChanged.connect(self.invalidate)
        self.seed.valueChanged.connect(self.invalidate)
        self.apply_preset()
        self.refresh_access()

    @staticmethod
    def set_card(box,code):
        box.blockSignals(True)
        box.setCurrentIndex(box.findData(code))
        box.blockSignals(False)

    def apply_preset(self,*_):
        hole,board,villain=PRESETS[self.preset.currentText()]
        self.load_cards(hole,board,villain)

    def load_cards(self,hole,board,villain=None):
        for box,code in zip(self.hole,hole):
            self.set_card(box,code)
        for i,box in enumerate(self.board):
            self.set_card(box,board[i] if i<len(board) else None)
        if villain:
            for box,code in zip(self.villain,villain):
                self.set_card(box,code)
        self.invalidate()

    def from_decision(self,decision):
        if not self.window.can_study():
            return
        self.mode.setCurrentIndex(self.mode.findData('random'))
        self.load_cards(decision.hole,decision.board)
        self.source_note=(f'Trouxemos apenas suas cartas e as cartas da mesa daquela decisão. Ela tinha {decision.opponents} adversários; '
                          'este laboratório usa uma comparação simplificada com apenas um. Não usa cartas privadas alheias nem analisa automaticamente o valor de sua jogada.')
        self.status.setText(self.source_note+' Clique em Simular.')

    def invalidate(self,*_):
        self.generation+=1
        self.source_note=''
        self.jobs.cancel()
        self.result=None
        if not hasattr(self,'canvas'):
            return
        hole=tuple(b.currentData() for b in self.hole)
        board=tuple(b.currentData() for b in self.board if b.currentData())
        villain=tuple(b.currentData() for b in self.villain) if self.mode.currentData()=='fixed' else ()
        self.initial=(hole,board,villain)
        self.canvas.set_cards(hole,board,villain)
        self.examples.blockSignals(True)
        self.examples.clear()
        self.examples.addItem('Cartas iniciais deste exemplo')
        self.examples.blockSignals(False)
        self.bars.result=None
        self.bars.update()
        self.output.clear()
        self.refresh_access()

    def refresh_access(self,*_):
        allowed=self.window.can_study() and not self.closing
        busy=self.jobs.busy
        for widget in self.inputs:
            widget.setEnabled(allowed and not busy)
        for widget in self.villain:
            widget.setEnabled(allowed and not busy and self.mode.currentData()=='fixed')
        self.run.setEnabled(allowed and not busy)
        self.cancel.setEnabled(busy)
        self.examples.setEnabled(allowed and not busy)
        if not allowed:
            self.generation+=1
            self.jobs.cancel()
            self.result=None
            self.canvas.set_cards()
            self.bars.result=None
            self.bars.update()
            self.output.clear()
            self.status.setText('Finalize a sessão de Avaliação para acessar o laboratório.')

    def start(self):
        if not self.window.can_study() or self.jobs.busy:
            return
        hole=tuple(b.currentData() for b in self.hole)
        board_slots=[b.currentData() for b in self.board]
        board=tuple(c for c in board_slots if c)
        if board_slots[:len(board)]!=list(board):
            self.status.setText('Preencha as cartas da mesa da esquerda para a direita, sem lacunas.')
            return
        mode=self.mode.currentData()
        opponent=tuple(b.currentData() for b in self.villain) if mode=='fixed' else None
        classes=tuple(self.window.ranges_panel.selected) if mode=='range' else None
        samples,seed=self.samples.value(),self.seed.value()
        generation=self.generation
        self.result=None
        self.hole_used=hole
        self.output.clear()
        self.bars.result=None
        self.bars.update()
        self.examples.clear()
        self.examples.addItem('Cartas iniciais deste exemplo')
        if self.jobs.start(lambda token,progress:simulate(hole,board,opponent=opponent,classes=classes,
                           samples=samples,seed=seed,token=token,progress=progress),
                           lambda result:self.receive(result,generation),self.failed,self.progress):
            self.status.setText('Sorteando possibilidades em segundo plano…')

    def progress(self,counts):
        self.status.setText(f'{counts[0]} de {counts[1]} possibilidades sorteadas. Você pode cancelar.')

    def failed(self,message):
        self.status.setText(message)

    def receive(self,result,generation=None):
        if (generation is not None and generation!=self.generation) or (self.jobs.task and self.jobs.task.token.event.is_set()):
            return
        if self.closing or not self.window.can_study():
            return
        self.result=result
        self.bars.result=result
        self.bars.update()
        text=((self.source_note+'\n\n' if self.source_note else '')+f'{result.samples} simulações: {result.wins} vitórias, {result.ties} empates, {result.losses} derrotas.\n\n'
              f'Equity = (vitórias + metade dos empates) ÷ simulações = {result.equity:.1%}. '
              'Isso é uma participação média no pote, não a chance de melhorar suas cartas.\n\n')
        if result.improved_category is not None:
            text+=(f'Categoria inicial: {result.initial_category}. Em {result.improved_category/result.samples:.1%} '
                   'das simulações ela passou para uma categoria superior. Esse indicador não conta só melhorar cartas de desempate; '
                   'também não garante vencer o adversário.\n\n')
        else:
            text+='Sem cartas da mesa não há uma combinação inicial de cinco cartas para comparar a categoria.\n\n'
        text+=(f'Faixa conservadora de amostragem (95%): {result.interval[0]:.1%} a {result.interval[1]:.1%}. '
               'Ela mede apenas a incerteza do sorteio sob estas hipóteses, não a incerteza sobre as mãos reais de um adversário.\n\n'+
               result.assumption+' Não há cálculo de valor de apostar, desistências, taxas ou potes separados.\n\n'
               'A mesma semente repete o exemplo. Os cenários abaixo são possibilidades sorteadas, não previsões de uma partida.')
        self.output.setPlainText(text)
        self.examples.blockSignals(True)
        self.examples.clear()
        self.examples.addItem('Cartas iniciais deste exemplo')
        for i,example in enumerate(result.examples):
            improved='categoria melhorou' if example.improved else 'sem subir de categoria'
            self.examples.addItem(f'Possibilidade {i+1}: {example.outcome} • {improved}')
        self.examples.blockSignals(False)
        self.status.setText('Simulação concluída. Compare as barras e explore as possibilidades sorteadas.')

    def show_example(self,index):
        if index>0 and self.result and index<=len(self.result.examples):
            ex=self.result.examples[index-1]
            self.canvas.set_cards(self.hole_used,ex.board,ex.opponent)
        elif hasattr(self,'initial'):
            self.canvas.set_cards(*self.initial)

    def shutdown(self):
        self.closing=True
        self.jobs.cancel()
