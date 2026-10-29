"""Widgets de cartas e revisão de snapshots, sem reconstruir estado final secreto."""
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,QTextBrowser,QSlider
from .coach import DecisionRecord, PokerCoachService
from .education import STAGES,cards_text

SUITS={'c':'♣','d':'♦','h':'♥','s':'♠'}


class CardsCanvas(QWidget):
    def __init__(self):
        super().__init__()
        self.hole,self.board,self.villain=(),(),()
        self.setMinimumHeight(265)
        self.setMinimumWidth(540)

    def set_cards(self,hole=(),board=(),villain=()):
        self.hole,self.board,self.villain=tuple(hole),tuple(board),tuple(villain)
        self.update()

    def paintEvent(self,event):
        p=QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        w,h=self.width(),self.height()
        p.setBrush(QColor('#123b35'))
        p.setPen(QColor('#355b53'))
        p.drawRoundedRect(QRectF(4,4,w-8,h-8),28,28)
        card_w,card_h=48,66
        def line(label,cards,count,x,y):
            p.setPen(QColor('#d9ede7'))
            p.setFont(QFont('Segoe UI',10))
            p.drawText(QRectF(x,y-26,max(160,count*58),23),Qt.AlignLeft,label)
            for k in range(count):
                card=cards[k] if k<len(cards) else None
                rect=QRectF(x+k*58,y,card_w,card_h)
                p.setBrush(QColor('#fff8ec' if card else '#243554'))
                p.setPen(QColor('#fff8ec' if card else '#405675'))
                p.drawRoundedRect(rect,6,6)
                if card:
                    p.setPen(QColor('#bf394f' if card[1] in 'dh' else '#142a36'))
                    p.setFont(QFont('Segoe UI',15,QFont.Bold))
                    p.drawText(rect,Qt.AlignCenter,('10' if card[0]=='T' else card[0])+SUITS[card[1]])
                else:
                    p.setPen(QColor('#9aaccb'))
                    p.drawText(rect,Qt.AlignCenter,'?')
        line('Cartas da mesa',self.board,5,w/2-145,40)
        line('Primeiro jogador' if self.villain else 'Suas cartas',self.hole,2,w/2-145,154)
        if self.villain:
            line('Segundo jogador',self.villain,2,w/2+30,154)
        else:
            p.setPen(QColor('#a9c2b7'))
            p.setFont(QFont('Segoe UI',10))
            p.drawText(QRectF(w/2+15,155,w/2-40,70),Qt.TextWordWrap,
                       'Cartas ainda não abertas ficam ocultas. Não revelamos as cartas dos adversários nesta revisão.')


class ReviewPanel(QWidget):
    def __init__(self,window):
        super().__init__()
        self.window=window
        self.records=[]
        self.items=[]
        self.index=0
        self.locked=False
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel('REVISÃO VISUAL • SUAS DECISÕES, UMA DE CADA VEZ'))
        self.notice=QLabel('Escolha uma mão concluída. A revisão usa o que você sabia antes de agir; não mostra cartas futuras.')
        self.notice.setWordWrap(True)
        lay.addWidget(self.notice)
        self.hand_choice=QComboBox()
        self.hand_choice.currentIndexChanged.connect(self.select_hand)
        lay.addWidget(self.hand_choice)
        controls=QHBoxLayout()
        self.previous=QPushButton('← Decisão anterior')
        self.previous.clicked.connect(lambda:self.step(-1))
        self.next=QPushButton('Próxima decisão →')
        self.next.clicked.connect(lambda:self.step(1))
        self.counter=QLabel()
        controls.addWidget(self.previous)
        controls.addWidget(self.counter)
        controls.addWidget(self.next)
        lay.addLayout(controls)
        self.slider=QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.select_step)
        lay.addWidget(self.slider)
        self.canvas=CardsCanvas()
        lay.addWidget(self.canvas)
        self.values=QLabel()
        self.values.setWordWrap(True)
        lay.addWidget(self.values)
        self.text=QTextBrowser()
        lay.addWidget(self.text,1)
        self.practice=QPushButton('Praticar a conta desta decisão')
        self.practice.clicked.connect(self.practice_price)
        lay.addWidget(self.practice)
        self.explore=QPushButton('Explorar possibilidades de cartas desta decisão')
        self.explore.clicked.connect(self.explore_equity)
        lay.addWidget(self.explore)
        self.render()

    def reload(self,hand_id=None):
        if not self.window.can_review():
            self.lock()
            return
        self.locked=False
        self.items=self.window.repo.hands()
        self.hand_choice.blockSignals(True)
        self.hand_choice.clear()
        for key,session,number,payload in self.items:
            self.hand_choice.addItem(f'Mão salva #{key} • sessão {session} • mão {number}',key)
        selected=next((i for i,item in enumerate(self.items) if item[0]==hand_id),0)
        self.hand_choice.setCurrentIndex(selected if self.items else -1)
        self.hand_choice.blockSignals(False)
        self.hand_choice.setEnabled(bool(self.items))
        self.select_hand(self.hand_choice.currentIndex())

    def lock(self):
        self.locked=True
        self.records=[]
        self.items=[]
        self.hand_choice.clear()
        self.hand_choice.setEnabled(False)
        self.notice.setText('Termine a mão para revisar. Na Avaliação, finalize também a sessão antes de estudar as decisões.')
        self.render()

    def select_hand(self,index):
        self.records=[]
        self.index=0
        if not self.locked and 0<=index<len(self.items):
            try:
                self.records=[DecisionRecord.model_validate(r) for r in self.items[index][3].get('decisions',[])]
            except ValueError:
                self.notice.setText('Não foi possível validar as decisões desta mão. O histórico textual continua disponível.')
        self.slider.blockSignals(True)
        self.slider.setRange(0,max(0,len(self.records)-1))
        self.slider.setValue(0)
        self.slider.blockSignals(False)
        self.render()

    def step(self,delta):
        self.slider.setValue(max(0,min(len(self.records)-1,self.index+delta)))

    def select_step(self,index):
        if 0<=index<len(self.records):
            self.index=index
        self.render()

    def render(self):
        available=bool(self.records) and not self.locked
        self.previous.setEnabled(available and self.index>0)
        self.next.setEnabled(available and self.index<len(self.records)-1)
        self.slider.setEnabled(available)
        self.practice.setEnabled(False)
        self.explore.setEnabled(available)
        if not available:
            self.canvas.set_cards()
            self.values.clear()
            self.counter.setText('Nenhuma decisão disponível')
            self.text.setPlainText('Mãos antigas podem ter apenas histórico textual. Jogue uma nova mão para registrar decisões revisáveis.'
                                   if not self.locked else 'Termine a mão para revisar. No modo Avaliação, finalize também a sessão.')
            return
        self.notice.setText('Esta é uma revisão das suas decisões registradas, não uma reprodução de todas as ações da mesa.')
        record=self.records[self.index]
        s=record.analysis.decision
        self.counter.setText(f'Decisão {self.index+1} de {len(self.records)} • {STAGES[s.street]}')
        self.canvas.set_cards(s.hole,s.board)
        self.values.setText(f'Antes de agir: {s.pot} fichas no centro • {s.stack} fichas disponíveis • '
                            f'{s.call} para acompanhar • {s.opponents} adversários ainda na mão')
        action={'fold':'desistiu','check':'passou sem pagar','call':'pagou para acompanhar',
                'raise':'apostou/aumentou','all-in':'colocou todas as fichas'}[record.action]
        self.text.setPlainText(f'Na partida, você {action}. Isso é um registro, não uma nota de qualidade.\n\n'+
                               PokerCoachService().explain(record.analysis).text)
        self.practice.setEnabled(record.analysis.price_percent is not None)

    def practice_price(self):
        if not self.window.can_review() or not self.records:
            return
        record=self.records[self.index]
        if record.analysis.price_percent is None:
            return
        s=record.analysis.decision
        self.window.training_panel.practice_decision(s)
        self.window.pages.setCurrentWidget(self.window.training_panel)


    def explore_equity(self):
        if not self.window.can_review() or not self.records:
            return
        self.window.equity_panel.from_decision(self.records[self.index].analysis.decision)
        self.window.pages.setCurrentWidget(self.window.equity_panel)
