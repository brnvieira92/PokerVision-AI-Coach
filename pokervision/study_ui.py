"""Plano de prática persistido, com metas explícitas e sem nota de rentabilidade."""
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QLabel,QPushButton,QListWidget,QTextBrowser
from .study import StudyPlan,make_plan,plan_status
from .training import TOPICS


class StudyPanel(QWidget):
    def __init__(self,window):
        super().__init__()
        self.window=window
        self.plan=None
        lay=QVBoxLayout(self)
        lay.addWidget(QLabel('PLANO DE ESTUDO • UM BLOCO DE CADA VEZ'))
        intro=QLabel('O plano escolhe três assuntos a partir das suas respostas. Cada bloco pede cinco novas respostas. '
                     'Terminar um bloco significa ter praticado, não dominar o assunto. Os acertos continuam separados no Meu progresso.')
        intro.setWordWrap(True)
        lay.addWidget(intro)
        self.summary=QLabel()
        self.summary.setWordWrap(True)
        lay.addWidget(self.summary)
        self.tasks=QListWidget()
        lay.addWidget(self.tasks)
        row=QHBoxLayout()
        self.start=QPushButton('Praticar o bloco selecionado ou o próximo')
        self.start.clicked.connect(self.practice)
        self.new=QPushButton('Montar novo plano com meus resultados')
        self.new.clicked.connect(self.regenerate)
        row.addWidget(self.start)
        row.addWidget(self.new)
        lay.addLayout(row)
        self.details=QTextBrowser()
        self.details.setPlainText('Como usar\n\n1. Selecione um bloco e pratique uma pergunta por vez.\n'
            '2. Leia a correção, inclusive quando acertar.\n3. Volte aqui para ver o avanço e siga para o próximo bloco.\n\n'
            'A escolha do assunto prioriza amostras pequenas e taxas recentes de acerto menores. '
            'Não usamos ganhos ou perdas fictícios para dizer que você aprendeu. '
            'Criar outro plano reinicia apenas as metas de prática; todas as respostas anteriores permanecem no histórico.')
        lay.addWidget(self.details,1)

    def reload(self):
        allowed=self.window.can_study()
        self.start.setEnabled(allowed)
        self.new.setEnabled(allowed)
        self.tasks.clear()
        if not allowed:
            self.summary.setText('Finalize a sessão de Avaliação para acessar seu plano de estudo.')
            return
        stored=self.window.repo.preference('study_plan')
        try:
            self.plan=StudyPlan.model_validate(stored) if stored else None
        except ValueError:
            self.plan=None
        if self.plan is None:
            self.regenerate()
            return
        status=plan_status(self.plan,self.window.repo.exercise_attempts())
        for i,row in enumerate(status):
            self.tasks.addItem(f"Bloco {i+1} — {TOPICS[row['topic']]}: {row['completed']} de {row['goal']} novas respostas")
        done=sum(r['completed']==r['goal'] for r in status)
        self.summary.setText(f'{done} de {len(status)} blocos praticados. Seu plano permanece salvo ao fechar o aplicativo.')
        next_index=next((i for i,r in enumerate(status) if r['completed']<r['goal']),0)
        self.tasks.setCurrentRow(next_index)

    def regenerate(self):
        if not self.window.can_study():
            return
        self.plan=make_plan(self.window.repo.exercise_attempts())
        self.window.repo.set_preference('study_plan',self.plan.model_dump(mode='json'))
        self.reload()

    def practice(self):
        if not self.window.can_study() or not self.plan:
            return
        row=self.tasks.currentRow()
        if not 0<=row<len(self.plan.tasks):
            return
        topic=self.plan.tasks[row].topic
        panel=self.window.training_panel
        panel.topic.setCurrentIndex(panel.topic.findData(topic))
        panel.new_exercise()
        self.window.pages.setCurrentWidget(panel)
