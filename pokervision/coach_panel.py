"""Painel de coach e diagnóstico; todo I/O ocorre em BackgroundJobs."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QPushButton, QComboBox, QCheckBox, QTextBrowser, QMessageBox)
from .coach import PokerCoachService, DecisionRecord, CoachReply, review_summary
from .ollama import OllamaProvider, MAIN_MODEL, ECONOMY_MODEL
from .resources import HardwareProfiler, RESOURCES
from .workers import BackgroundJobs


class CoachPanel(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.closing = False
        self.provider = OllamaProvider()
        self.service = PokerCoachService(self.provider)
        self.jobs = BackgroundJobs(self)
        self.jobs.busy_changed.connect(self.update_buttons)
        self.records, self.active_analysis = [], None
        self.stream_size = 0
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('COACH LOCAL • EXPLICAÇÕES PARA APRENDER'))
        intro = QLabel('Escolha uma decisão para entender seu preço e suas opções. A IA organiza explicações '
                       'verificadas; não adivinha cartas e não escolhe uma jogada ótima. Sem IA, o guia continua funcionando.')
        intro.setWordWrap(True)
        layout.addWidget(intro)
        form = QFormLayout()
        self.mode = QComboBox()
        for title, value in [('Sem LLM — guia verificado', 'off'), ('Econômico — Qwen3 0.6B', 'economy'),
                             ('Equilibrado — Qwen3 1.7B', 'balanced')]:
            self.mode.addItem(title, value)
        self.mode.setCurrentIndex(max(0, self.mode.findData(window.repo.preference('ai_mode', 'off'))))
        self.model = QComboBox()
        self.model.addItem('Automático: preferir Qwen3 do modo escolhido', None)
        self.cpu = QCheckBox('Usar somente CPU nas solicitações de IA')
        self.cpu.setChecked(window.repo.preference('ai_cpu', False))
        form.addRow('Uso de IA', self.mode)
        form.addRow('Modelo instalado', self.model)
        form.addRow(self.cpu)
        layout.addLayout(form)
        self.mode.currentIndexChanged.connect(self.save_preferences)
        self.cpu.toggled.connect(self.save_preferences)
        self.model.currentIndexChanged.connect(self.save_preferences)
        tools = QHBoxLayout()
        self.diagnose_button = QPushButton('Verificar computador e Ollama')
        self.diagnose_button.clicked.connect(self.diagnose)
        self.pull_choice = QComboBox()
        self.pull_choice.addItems([ECONOMY_MODEL, MAIN_MODEL])
        self.pull_button = QPushButton('Baixar modelo…')
        self.pull_button.clicked.connect(self.confirm_pull)
        self.unload_button = QPushButton('Liberar modelo da memória')
        self.unload_button.clicked.connect(self.unload)
        for w in (self.diagnose_button, self.pull_choice, self.pull_button, self.unload_button):
            tools.addWidget(w)
        layout.addLayout(tools)
        self.diagnostic = QTextBrowser()
        self.diagnostic.setMaximumHeight(165)
        self.diagnostic.setPlainText('Nenhuma verificação feita. Não é necessário instalar Ollama para jogar. '
                                     'Nenhum modelo será baixado sem sua confirmação.')
        layout.addWidget(self.diagnostic)
        self.summary = QLabel('Termine uma mão para revisar suas decisões. Históricos antigos podem não ter snapshots de decisões.')
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.review_choice = QComboBox()
        self.review_choice.currentIndexChanged.connect(self.select_record)
        layout.addWidget(self.review_choice)
        controls = QHBoxLayout()
        self.focus = QComboBox()
        for title, value in [('Entender o preço de pagar', 'price'), ('O que cada opção faz', 'options'),
                             ('Entender minha posição', 'position'), ('Entender minhas cartas e a mesa', 'cards')]:
            self.focus.addItem(title, value)
        self.explain_button = QPushButton('Explicar decisão selecionada')
        self.explain_button.clicked.connect(self.explain_selected)
        self.finish_button = QPushButton('Finalizar sessão e revisar')
        self.finish_button.clicked.connect(window.finish_training_session)
        self.cancel_button = QPushButton('Cancelar solicitação')
        self.cancel_button.clicked.connect(self.jobs.cancel)
        for w in (self.focus, self.explain_button, self.finish_button, self.cancel_button):
            controls.addWidget(w)
        layout.addLayout(controls)
        self.progress = QLabel('Pronto. Uma solicitação de IA por vez.')
        self.progress.setWordWrap(True)
        layout.addWidget(self.progress)
        self.output = QTextBrowser()
        self.output.setPlainText('Durante a Aprendizagem, use “Pedir explicação” na mesa. '
                                 'Na Avaliação, as explicações ficam disponíveis ao finalizar a sessão.')
        layout.addWidget(self.output, 1)
        self.update_buttons()

    def save_preferences(self, *_):
        self.window.repo.set_preference('ai_mode', self.mode.currentData())
        self.window.repo.set_preference('ai_cpu', self.cpu.isChecked())
        self.window.repo.set_preference('ai_model', self.model.currentData())

    def update_buttons(self, *_):
        busy = self.jobs.busy
        for widget in (self.diagnose_button, self.pull_button, self.unload_button):
            widget.setEnabled(not busy)
        self.cancel_button.setEnabled(busy)
        self.explain_button.setEnabled(not busy and self.active_analysis is not None and self.window.can_review())
        self.finish_button.setEnabled(not busy and self.window.table.finished and self.window.session is not None)
        for widget in (self.mode, self.model, self.cpu, self.pull_choice):
            widget.setEnabled(not busy)

    def diagnostic_result(self, result):
        if self.closing:
            return
        hardware, models, error = result
        lines = [hardware.system, f'Processador: {hardware.processor} • {hardware.cpu_count} núcleos lógicos',
                 f'RAM: {hardware.ram_available_gb:.1f} GB disponíveis de {hardware.ram_total_gb:.1f} GB',
                 f'CPU (amostra): {hardware.cpu_percent:.0f}% • memória do aplicativo: {hardware.app_ram_mb:.0f} MB']
        for gpu in hardware.gpus:
            lines.append(f"GPU: {gpu['name']} • VRAM livre/total: {gpu['vram_free_mb']:.0f}/{gpu['vram_total_mb']:.0f} MB • driver {gpu['driver']}")
        lines.append(hardware.gpu_note)
        if hardware.ram_available_gb < 1.5:
            lines.append('Menos de 1,5 GB livres: o coach usará o guia sem LLM até haver mais memória disponível.')
        elif hardware.ram_available_gb < 3:
            lines.append('Menos de 3 GB livres: o modo Equilibrado passa ao Econômico automaticamente.')
        lines.append('Ollama: ' + (error if error else f'conectado; {len(models)} modelos locais instalados.'))
        if not self.provider.choose_model(models, self.mode.currentData()):
            lines.append('Qwen3 recomendado ausente. Escolha outro modelo local listado ou baixe um dos modelos recomendados.')
        self.diagnostic.setPlainText('\n'.join(lines))
        preferred = self.window.repo.preference('ai_model')
        self.model.blockSignals(True)
        self.model.clear()
        self.model.addItem('Automático: preferir Qwen3 do modo escolhido', None)
        for model in models:
            self.model.addItem(model, model)
        self.model.setCurrentIndex(max(0, self.model.findData(preferred)))
        self.model.blockSignals(False)
        self.progress.setText('Verificação concluída. Os modelos só são carregados quando você pede uma explicação.')

    def diagnose(self):
        def operation(token, progress):
            hardware = HardwareProfiler().profile()
            token.check()
            try:
                models, error = self.provider.models(token), ''
            except Exception as exc:
                token.check()
                models, error = [], str(exc)
            return hardware, models, error
        if self.jobs.start(operation, self.diagnostic_result, self.failed):
            self.progress.setText('Verificando hardware e serviço local…')

    def confirm_pull(self):
        model = self.pull_choice.currentText()
        answer = QMessageBox.question(self, 'Autorizar download de modelo',
            f'Baixar {model} pelo Ollama local? Isso usa internet e espaço em disco '
            '(aproximadamente 0,5 GB para 0.6B ou 1,4 GB para 1.7B; pode variar). '
            'O aplicativo não instalará nem iniciará o Ollama por você.')
        if answer == QMessageBox.Yes:
            self.start_pull(model)

    def start_pull(self, model):
        # Chamado exclusivamente após a confirmação explícita do diálogo acima.
        if self.jobs.start(lambda token, progress: self.provider.pull(model, authorized=True,
                           token=token, progress=progress), self.pull_done, self.failed, self.pull_progress):
            self.progress.setText('Baixando modelo autorizado… Você pode cancelar.')

    def pull_progress(self, event):
        status = str(event.get('status', 'Baixando'))
        completed, total = event.get('completed', 0), event.get('total', 0)
        self.progress.setText(f'{status} • {completed*100/total:.0f}%' if total else status)

    def pull_done(self, _):
        self.progress.setText('Download concluído. Clique em Verificar computador e Ollama para atualizar os modelos.')

    def unload(self):
        model = self.model.currentData()
        if not model:
            model = self.provider.choose_model([self.model.itemData(i) for i in range(1, self.model.count())],
                                               self.mode.currentData())
        if not model:
            self.progress.setText('Verifique o Ollama e selecione um modelo instalado para liberar.')
            return
        if self.jobs.start(lambda token, progress: self.provider.unload(model, token),
                           self.unload_done, self.failed):
            self.progress.setText('Solicitando liberação do modelo…')

    def unload_done(self, _):
        self.progress.setText('Liberação solicitada ao Ollama. O simulador permanece disponível.')

    def load_review(self, records, title='Revisão de decisões'):
        self.clear_context()
        self.records = [r if isinstance(r, DecisionRecord) else DecisionRecord.model_validate(r) for r in records]
        self.summary.setText(title)
        self.output.setPlainText(review_summary(self.records))
        self.review_choice.blockSignals(True)
        self.review_choice.clear()
        for i, record in enumerate(self.records):
            d = record.analysis.decision
            action = {'fold': 'desistiu', 'check': 'passou', 'call': 'pagou', 'raise': 'aumentou', 'all-in': 'todas as fichas'}[record.action]
            self.review_choice.addItem(f'Decisão {i+1} • Mão {d.hand} • {action}')
        self.review_choice.blockSignals(False)
        self.select_record(self.review_choice.currentIndex())

    def select_record(self, index):
        self.jobs.cancel()
        self.active_analysis = self.records[index].analysis if 0 <= index < len(self.records) else None
        if self.active_analysis and self.window.can_review():
            s = self.active_analysis.decision
            text = PokerCoachService().explain(self.active_analysis).text
            cached = self.window.repo.coach_report(s.id)
            if cached:
                try:
                    reply = CoachReply.model_validate(cached)
                    if reply.analysis_id == s.id:
                        text = reply.text
                except ValueError:
                    pass
            self.output.setPlainText(review_summary(self.records) + '\n\n' +
                f'Decisão selecionada: mão {s.hand}, antes de agir.\n\n' + text)
        self.update_buttons()

    def clear_context(self):
        self.jobs.cancel()
        self.active_analysis = None
        self.records = []
        self.review_choice.clear()
        self.output.clear()
        self.summary.setText('Uma nova mão/sessão começou. A revisão usará somente decisões concluídas.')
        self.update_buttons()

    def request_current(self, analysis):
        if self.jobs.busy:
            self.progress.setText('Há uma solicitação em andamento. Cancele ou aguarde antes de pedir outra.')
            return
        self.active_analysis = analysis
        self.explain(analysis)

    def explain_selected(self):
        if self.active_analysis and self.window.can_review():
            self.explain(self.active_analysis)

    def explain(self, analysis):
        if not self.window.can_explain(analysis):
            self.output.setPlainText('Esta explicação não está disponível durante uma mão de Avaliação.')
            return
        mode, model, cpu, focus = self.mode.currentData(), self.model.currentData(), self.cpu.isChecked(), self.focus.currentData()
        self.stream_size = 0
        self.summary.setText(f'Mão {analysis.decision.hand} • dados anteriores à decisão • sem resultado futuro')
        # Mostra uma explicação verificada imediatamente; tokens brutos nunca são publicados.
        fallback = PokerCoachService().explain(analysis, mode='off', focus=focus)
        self.output.setPlainText(fallback.text)
        if self.jobs.start(lambda token, progress: self.service.explain(analysis, mode=mode, model=model,
                           cpu=cpu, token=token, progress=progress, focus=focus),
                           self.receive_reply, self.failed, self.stream_progress):
            self.progress.setText('Preparando explicação local… A mesa continua respondendo.')

    def stream_progress(self, chunk):
        self.stream_size += len(chunk)
        self.progress.setText(f'Recebendo resposta local: {self.stream_size} caracteres. '
                              'O conteúdo só será publicado depois de validado.')

    def receive_reply(self, reply):
        if self.closing or not self.active_analysis or reply.analysis_id != self.active_analysis.decision.id:
            return
        if not self.window.can_explain(self.active_analysis):
            return
        self.window.repo.save_coach(reply)
        self.output.setPlainText(reply.text)
        self.progress.setText(('IA local: ' + reply.model if reply.source == 'ollama' else 'Explicação verificada, sem LLM.') +
                              ('\n' + reply.reason if reply.reason else ''))

    def failed(self, message):
        self.progress.setText(message)

    def shutdown(self):
        self.closing = True
        self.active_analysis = None
        self.jobs.cancel()
