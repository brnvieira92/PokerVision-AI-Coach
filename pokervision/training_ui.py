"""Treinamento e dashboard locais; não dependem de geração por LLM."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QComboBox,
    QRadioButton,QButtonGroup,QTextBrowser,QTableWidget,QTableWidgetItem,QHeaderView,QAbstractItemView)
from .training import ExerciseFactory,TOPICS,topic_progress,recommend_topic
from .review import CardsCanvas
from .ranges import DESC,PRESETS,POSITION_GUIDE,matrix_class,combo_count


class TrainingPanel(QWidget):
    def __init__(self,window):
        super().__init__()
        self.window=window
        self.factory=ExerciseFactory()
        self.exercise=None
        self.answered=False
        self.access_allowed=None
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel('TREINAMENTO • PRATIQUE, ENTENDA E REPITA'))
        intro=QLabel('Responda uma pergunta por vez. A correção explica a conta ou a regra. '
                     'O progresso considera sua primeira resposta; depois da correção, gere um novo exercício.')
        intro.setWordWrap(True)
        lay.addWidget(intro)
        row=QHBoxLayout()
        self.topic=QComboBox()
        self.topic.addItem('Recomendado para mim',None)
        for key,title in TOPICS.items():
            self.topic.addItem(title,key)
        row.addWidget(self.topic)
        self.new_button=QPushButton('Novo exercício')
        self.new_button.clicked.connect(self.new_exercise)
        row.addWidget(self.new_button)
        lay.addLayout(row)
        self.recommendation=QLabel()
        self.recommendation.setWordWrap(True)
        lay.addWidget(self.recommendation)
        self.prompt=QLabel('Clique em Novo exercício para começar. Não é necessário abrir uma mesa ou ativar a IA.')
        self.prompt.setWordWrap(True)
        self.prompt.setStyleSheet('font-size:17px; padding:12px;')
        lay.addWidget(self.prompt)
        self.canvas=CardsCanvas()
        self.canvas.hide()
        lay.addWidget(self.canvas)
        self.choice_layout=QVBoxLayout()
        self.group=QButtonGroup(self)
        lay.addLayout(self.choice_layout)
        self.submit=QPushButton('Conferir minha resposta')
        self.submit.clicked.connect(self.answer)
        lay.addWidget(self.submit)
        self.feedback=QTextBrowser()
        lay.addWidget(self.feedback,1)
        self.refresh_access()

    def refresh_access(self):
        allowed=self.window.can_study()
        self.access_allowed=allowed
        self.new_button.setEnabled(allowed)
        self.topic.setEnabled(allowed)
        self.submit.setEnabled(allowed and self.exercise is not None and not self.answered)
        for button in self.group.buttons():
            button.setEnabled(allowed and not self.answered)
        if not allowed:
            self.exercise=None
            self.clear_choices()
            self.canvas.set_cards()
            self.canvas.hide()
            self.prompt.setText('Na Avaliação, finalize a sessão para acessar os exercícios e as correções.')
            self.feedback.clear()
        progress=topic_progress(self.window.repo.exercise_attempts())
        recommended=recommend_topic(progress)
        self.recommendation.setText(f'Próximo assunto sugerido: {TOPICS[recommended]}. '
            'Primeiro buscamos três respostas por assunto; depois priorizamos o menor acerto nas últimas vinte respostas.')

    def clear_choices(self):
        for button in self.group.buttons():
            self.group.removeButton(button)
            self.choice_layout.removeWidget(button)
            button.deleteLater()

    def display(self,exercise):
        self.exercise,self.answered=exercise,False
        self.clear_choices()
        self.prompt.setText(TOPICS[exercise.topic]+'\n\n'+exercise.prompt)
        self.feedback.clear()
        for choice in exercise.choices:
            button=QRadioButton(choice.label)
            button.setProperty('choice_key',choice.key)
            self.group.addButton(button)
            self.choice_layout.addWidget(button)
        show=bool(exercise.hole or exercise.board)
        self.canvas.setVisible(show)
        self.canvas.set_cards(exercise.hole,exercise.board,exercise.villain)
        self.refresh_access()

    def new_exercise(self):
        if not self.window.can_study():
            return
        topic=self.topic.currentData() or recommend_topic(topic_progress(self.window.repo.exercise_attempts()))
        self.display(self.factory.generate(topic))

    def practice_decision(self,snapshot):
        if self.window.can_study():
            self.display(self.factory.price(snapshot.pot,snapshot.call,snapshot.id))
            self.recommendation.setText('Exercício criado com o pote e o pagamento daquela decisão. '
                                        'Você está praticando a conta, não julgando a jogada pelo resultado.')

    def answer(self):
        if not self.window.can_study() or not self.exercise or self.answered:
            return
        chosen=self.group.checkedButton()
        if not chosen:
            self.feedback.setPlainText('Escolha uma resposta antes de conferir. Isso ainda não conta como tentativa.')
            return
        feedback=self.window.repo.answer_exercise(self.exercise,chosen.property('choice_key'))
        self.answered=True
        self.feedback.setPlainText(('Você acertou!' if feedback.correct else 'Vamos entender esta resposta.')+
            f'\n\nSua resposta: {feedback.chosen}\nResposta correta: {feedback.expected}\n\n'+feedback.explanation)
        self.refresh_access()
        self.window.progress_panel.reload()


class ProgressPanel(QWidget):
    def __init__(self,window):
        super().__init__()
        self.window=window
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel('SEU PROGRESSO • APRENDIZADO POR ASSUNTO'))
        self.summary=QLabel()
        self.summary.setWordWrap(True)
        self.summary.setStyleSheet('font-size:18px;padding:12px;')
        lay.addWidget(self.summary)
        self.table=QTableWidget(len(TOPICS),5)
        self.table.setHorizontalHeaderLabels(['Assunto','Respostas','Acertos','Percentual','Faixa aproximada (95%)'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().hide()
        lay.addWidget(self.table)
        self.note=QLabel('A faixa mostra a incerteza da porcentagem de acertos; poucas respostas produzem uma faixa ampla. '
                         'Exercícios relacionados não são amostras totalmente independentes: a faixa é ilustrativa, '
                         'não certifica habilidade. Uma vitória em fichas não entra na nota de exercícios.')
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        self.suggestion=QLabel()
        self.suggestion.setWordWrap(True)
        lay.addWidget(self.suggestion)
        self.practice=QPushButton('Praticar o assunto selecionado (ou o recomendado)')
        self.practice.clicked.connect(self.start_practice)
        lay.addWidget(self.practice)
        self.recent=QTextBrowser()
        lay.addWidget(self.recent,1)
        self.reload()

    def reload(self):
        attempts=self.window.repo.exercise_attempts()
        self.progress=topic_progress(attempts)
        total=len(attempts)
        hits=sum(a['correct'] for a in attempts)
        sessions,hands=self.window.repo.stats()
        self.summary.setText(f'{total} '+('exercício respondido' if total==1 else 'exercícios respondidos')+
            f' • {hits} '+('acerto' if hits==1 else 'acertos')+
            f' • {hands} '+('mão simulada' if hands==1 else 'mãos simuladas')+
            f' • {sessions} '+('sessão' if sessions==1 else 'sessões'))
        for row,(key,title) in enumerate(TOPICS.items()):
            stats=self.progress[key]
            n,c=stats['total'],stats['correct']
            interval=stats['interval']
            cells=[title,str(n),str(c),f'{c/n:.0%}' if n else 'Sem amostra',
                   f'{interval[0]:.0%} a {interval[1]:.0%}' if interval else 'Ainda sem estimativa']
            for col,value in enumerate(cells):
                self.table.setItem(row,col,QTableWidgetItem(value))
        topic=recommend_topic(self.progress)
        self.suggestion.setText(f'Sugestão de estudo: {TOPICS[topic]}. '
            'A sugestão equilibra assuntos ainda pouco praticados e acertos recentes. Não é uma classificação para torneios reais.')
        recent=attempts[-10:]
        lines=[]
        for a in reversed(recent):
            options={c['key']:c['label'] for c in a['exercise']['choices']}
            lines.append(f"{TOPICS[a['topic']]} — {'Acertou' if a['correct'] else 'Revisar'}\n"
                         f"{a['exercise']['prompt']}\nSua resposta: {options[a['chosen']]}\n")
        self.recent.setPlainText('Últimas respostas\n\n'+'\n'.join(lines) if lines else
                                 'Ainda não há respostas. Comece com um exercício; seu progresso será salvo automaticamente.')
        self.practice.setEnabled(self.window.can_study())

    def start_practice(self):
        if not self.window.can_study():
            return
        row=self.table.currentRow()
        key=list(TOPICS)[row] if 0<=row<len(TOPICS) else recommend_topic(self.progress)
        panel=self.window.training_panel
        panel.topic.setCurrentIndex(panel.topic.findData(key))
        panel.new_exercise()
        self.window.pages.setCurrentWidget(panel)


class RangesPanel(QWidget):
    def __init__(self,window):
        super().__init__()
        self.window=window
        self.selected=set()
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel('MÃOS INICIAIS • APRENDA A LER UM CONJUNTO DE MÃOS'))
        intro=QLabel('Um conjunto de mãos possíveis é chamado range. Os exemplos abaixo foram feitos para aprender '
                     'a ler o quadro: não são uma tabela de jogadas obrigatórias ou uma solução ótima. '
                     'A posição, as apostas anteriores, os saldos de fichas e os adversários mudam a decisão.')
        intro.setWordWrap(True)
        lay.addWidget(intro)
        row=QHBoxLayout()
        self.position=QComboBox()
        self.position.addItems(POSITION_GUIDE)
        self.preset=QComboBox()
        self.preset.addItems(PRESETS)
        row.addWidget(self.position)
        row.addWidget(self.preset)
        lay.addLayout(row)
        self.position_text=QLabel()
        self.position_text.setWordWrap(True)
        lay.addWidget(self.position_text)
        self.table=QTableWidget(13,13)
        self.table.setHorizontalHeaderLabels([('10' if c=='T' else c) for c in DESC])
        self.table.setVerticalHeaderLabels([('10' if c=='T' else c) for c in DESC])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setMinimumHeight(340)
        self.table.cellClicked.connect(self.toggle)
        lay.addWidget(self.table,1)
        self.summary=QLabel()
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        self.detail=QLabel('Clique em uma célula para incluir ou retirar essa classe do seu conjunto e ver seu significado.')
        self.detail.setWordWrap(True)
        lay.addWidget(self.detail)
        legend=QLabel('Diagonal: pares. Acima: mesmo naipe (s). Abaixo: naipes diferentes (o). '
                      'A = Ás, K = Rei, Q = Dama, J = Valete, T = 10. Células verdes estão incluídas.')
        legend.setWordWrap(True)
        lay.addWidget(legend)
        self.position.currentIndexChanged.connect(self.describe_position)
        self.preset.currentIndexChanged.connect(self.apply_preset)
        self.describe_position()
        self.apply_preset()

    def describe_position(self,*_):
        self.position_text.setText(POSITION_GUIDE[self.position.currentText()])

    def apply_preset(self,*_):
        self.selected=set(PRESETS[self.preset.currentText()])
        self.draw()

    def draw(self):
        for row in range(13):
            for col in range(13):
                label=matrix_class(row,col)
                item=QTableWidgetItem(label)
                item.setTextAlignment(Qt.AlignCenter)
                item.setBackground(QColor('#235b4c' if label in self.selected else '#19283a'))
                item.setToolTip(f'{label}: {6 if len(label)==2 else 4 if label.endswith("s") else 12} combinações de duas cartas')
                self.table.setItem(row,col,item)
        count=combo_count(self.selected)
        self.summary.setText(f'{len(self.selected)} classes incluídas • {count} das 1326 combinações possíveis ({count/1326:.1%}). '
                             'Contagem antes de conhecer qualquer carta; todas as combinações de cada classe selecionada estão incluídas.')

    def toggle(self,row,col):
        if not self.window.can_study():
            return
        label=matrix_class(row,col)
        if label in self.selected:
            self.selected.remove(label)
        else:
            self.selected.add(label)
        self.preset.blockSignals(True)
        self.preset.setCurrentText('Seu conjunto (clique para editar)')
        self.preset.blockSignals(False)
        kind='um par' if len(label)==2 else 'duas cartas do mesmo naipe' if label.endswith('s') else 'duas cartas de naipes diferentes'
        self.detail.setText(f'{label} representa {kind}. '
                            'Selecionar uma célula monta um conjunto para estudo; não é uma ordem para apostar com essa mão.')
        self.draw()

    def refresh_access(self):
        allowed=self.window.can_study()
        self.setEnabled(allowed)
        if not allowed:
            self.detail.setText('Finalize a sessão de Avaliação para estudar conjuntos de mãos.')
