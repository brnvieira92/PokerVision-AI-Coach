"""Mesa desenhada reutilizável, sem regras de jogo próprias."""
import math
from PySide6.QtCore import Qt,QRectF,QTimeLine
from PySide6.QtGui import QColor,QPainter,QFont
from PySide6.QtWidgets import QWidget
from .education import STAGES
SUITS={'c':'♣','d':'♦','h':'♥','s':'♠'}


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
        p.drawText(QRectF(0, h/2-55, w, 25), Qt.AlignCenter, getattr(self.window,'table_caption','POKERVISION / CASH LAB'))
        t = self.window.table
        p.setPen(QColor('#ecdbab'))
        p.drawText(QRectF(0, h/2+40, w, 30), Qt.AlignCenter,
                   f'Fichas no centro: {t.pot}  ·  {STAGES[t.street]}  ·  Mão {t.number}')

        def card(x, y, c=None):
            p.setPen(QColor('#364a68' if c is None else '#fff8ec'))
            p.setBrush(QColor('#243554' if c is None else '#fff8ec'))
            p.drawRoundedRect(QRectF(x, y, 39, 54), 5, 5)
            if c:
                p.setPen(QColor('#bf394f' if c[1] in 'dh' else '#142a36'))
                p.setFont(QFont('Segoe UI', 13 if c[0] == 'T' else 14, QFont.Bold))
                p.drawText(QRectF(x, y, 39, 54), Qt.AlignCenter, ('10' if c[0] == 'T' else c[0])+SUITS[c[1]])
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
            y = min(y, h-94)
            p.setPen(QColor('#63e0b0' if t.actor == i else '#3a4a60'))
            p.setBrush(QColor('#19283a'))
            p.drawRoundedRect(QRectF(x-76, y-29, 152, 58), 12, 12)
            p.setFont(QFont('Segoe UI', 10, QFont.Bold))
            p.setPen(QColor('#96a4b6' if player.folded else '#edf4ff'))
            badges = (' • Botão' if i == t.button else '') + (' • Menor' if i == getattr(t, 'sb', -1) else '') + (' • Maior' if i == getattr(t, 'bb', -1) else '')
            p.drawText(QRectF(x-74, y-25, 148, 25), Qt.AlignCenter, player.name+badges)
            p.drawText(QRectF(x-74, y, 148, 25), Qt.AlignCenter,
                       f'{player.stack} fichas  ·  aposta {player.bet}')
            cy = y+34
            for k, c in enumerate(player.hole):
                reveal = i == self.window.hero or (t.finished and not player.folded)
                card(x-42+k*45, cy, c if reveal else None)
