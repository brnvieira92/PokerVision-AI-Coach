"""Coach didático: snapshots sem cartas alheias nem resultados futuros.

O LLM seleciona explicações de um catálogo verificado; não publica prosa livre
ou números inventados. O modo sem LLM usa o mesmo catálogo diretamente.
"""
from collections import Counter
import json
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .cards import validate
from .education import STAGES, cards_text
from .math_engine import pot_odds
from .ollama import OllamaError
from .resources import RESOURCES

ACTIONS = Literal['fold', 'check', 'call', 'raise', 'all-in']
LESSONS = Literal['price', 'options', 'position', 'limits', 'cards']


class DecisionSnapshot(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    id: str = Field(default_factory=lambda: uuid4().hex)
    hand: int = Field(ge=1)
    street: Literal['preflop', 'flop', 'turn', 'river']
    hole: tuple[str, str]
    board: tuple[str, ...]
    pot: int = Field(ge=0)
    call: int = Field(ge=0)
    stack: int = Field(ge=0)
    hero_bet: int = Field(ge=0)
    current_bet: int = Field(ge=0)
    raise_min: int = Field(ge=0)
    raise_max: int = Field(ge=0)
    actions: tuple[ACTIONS, ...]
    opponents: int = Field(ge=1, le=8)
    on_button: bool
    small_blind: bool
    big_blind: bool
    complex_pots: bool

    @model_validator(mode='after')
    def valid_cards(self):
        validate(list(self.hole + self.board))
        expected = {'preflop': 0, 'flop': 3, 'turn': 4, 'river': 5}
        if len(self.board) != expected[self.street] or self.call > self.stack:
            raise ValueError('Snapshot incompatível com a decisão')
        return self


def snapshot(table, hero):
    if table.finished or table.actor != hero:
        raise ValueError('Capture somente uma decisão atual do usuário')
    p, legal = table.players[hero], table.legal()
    actions = ['fold']
    if legal['check']:
        actions.append('check')
    if legal['call']:
        actions.append('call')
    if legal['raise_allowed']:
        actions.append('raise')
    if legal['all_in']:
        actions.append('all-in')
    return DecisionSnapshot(hand=table.number, street=table.street, hole=tuple(p.hole),
        board=tuple(table.board), pot=table.pot, call=legal['call'], stack=p.stack,
        hero_bet=p.bet, current_bet=table.current, raise_min=legal['minimum'],
        raise_max=legal['maximum'], actions=tuple(actions), opponents=len(table._live())-1,
        on_button=hero == table.button, small_blind=hero == table.sb, big_blind=hero == table.bb,
        complex_pots=legal['call'] < max(0, table.current-p.bet) or
        any(not other.folded and other.stack == 0 for other in table.players))


class DecisionAnalysis(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    decision: DecisionSnapshot
    price_percent: float | None
    assumptions: tuple[str, ...]
    missing: tuple[str, ...] = ('Cartas e mãos possíveis dos adversários',
                                'Apostas futuras', 'Probabilidade real de vencer ou dividir')

    @model_validator(mode='after')
    def verified_price(self):
        s = self.decision
        expected = round(pot_odds(s.pot, s.call)*100, 2) if s.call and not s.complex_pots else None
        if self.price_percent != expected:
            raise ValueError('Preço não corresponde à fórmula verificada')
        return self


def analyze(decision):
    price = round(pot_odds(decision.pot, decision.call)*100, 2) if decision.call and not decision.complex_pots else None
    return DecisionAnalysis(decision=decision, price_percent=price,
        assumptions=('Sem novas apostas depois de pagar', 'Sem retirada de taxa do pote',
                     'A conta de preço não estima a força das cartas'))


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    analysis: DecisionAnalysis
    action: ACTIONS
    amount: int | None = None


class LessonChoice(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    analysis_id: str
    pot: int
    call: int
    price_percent: float | None
    lesson_ids: list[LESSONS] = Field(min_length=1, max_length=5)
    uncertainty: Literal['informações insuficientes para escolher a melhor jogada']


class CoachReply(BaseModel):
    analysis_id: str
    source: Literal['deterministic', 'ollama']
    text: str
    reason: str = ''
    model: str | None = None


def lessons(analysis):
    s = analysis.decision
    if not s.call:
        price = 'Você pode passar a vez sem pagar. Não há aposta para cobrir agora.'
    elif analysis.price_percent is None:
        price = (f'Para acompanhar, você precisa pagar mais {s.call} fichas. '
                 'Há uma aposta com todas as fichas ou possíveis potes separados. '
                 'Não uso a conta simplificada com o pote inteiro neste caso.')
    else:
        total = s.pot+s.call
        price = (f'Havia {s.pot} fichas no centro. Pagar mais {s.call} deixaria {total} em disputa. '
                 f'O preço é {s.call} ÷ {total} = {analysis.price_percent:g}%. '
                 'Esse número não é sua chance de ganhar. Sem novas apostas ou taxa, seria preciso '
                 f'receber em média pelo menos {analysis.price_percent:g}% desse pote para compensar o pagamento.')
    labels = {'fold': 'Desistir: deixa de disputar e mantém no centro o que já apostou.',
              'check': 'Passar: continua sem pagar nada agora.',
              'call': f'Pagar: acrescenta {s.call} fichas para acompanhar.',
              'raise': f'Apostar/Aumentar: escolhe um total na rodada entre {min(s.raise_min,s.raise_max)} e {s.raise_max} fichas, incluindo o que já colocou.',
              'all-in': f'Todas as fichas: coloca suas {s.stack} fichas restantes em jogo.'}
    position = ('Você está no botão, a marca que anda a cada mão. ' if s.on_button else
                'Você colocou a aposta obrigatória menor. ' if s.small_blind else
                'Você colocou a aposta obrigatória maior. ' if s.big_blind else
                'A ordem de jogar depende de onde você está em relação ao botão. ')
    position += ('Antes de abrir as cartas, a ordem é diferente de depois. Agir depois dos outros '
                 'permite observar as ações deles antes de decidir; isso se chama vantagem de posição.')
    return dict(price=price, options='\n'.join(labels[a] for a in s.actions), position=position,
                limits=('Ainda não sabemos as cartas dos outros jogadores nem quanto apostarão depois. '
                        'Por isso, estas informações não provam qual ação é a melhor. '
                        'Ganhar ou perder depois não muda o que era conhecido nesta decisão.'),
                cards=f'Suas cartas: {cards_text(s.hole)}. Mesa: {cards_text(s.board)}. {STAGES[s.street]}. '
                      'Todos podem usar as cartas do centro para formar a melhor combinação de cinco cartas.')


class PokerCoachService:
    def __init__(self, provider=None, resources=RESOURCES):
        self.provider, self.resources = provider, resources

    def explain(self, analysis, *, mode='off', model=None, cpu=False, token=None,
                progress=None, focus='price'):
        from .resources import CancelToken
        token = token or CancelToken()
        token.check()
        catalog = lessons(analysis)
        order = list(dict.fromkeys([focus, 'price', 'options', 'limits']))
        reason, source, actual_model = '', 'deterministic', None
        requested = mode
        mode = self.resources.mode_for_memory(mode)
        if mode == 'off' and requested != 'off':
            reason = 'Pouca memória disponível: explicação verificada sem carregar IA.'
        elif mode != 'off' and self.provider:
            try:
                with self.resources.inference(token):
                    installed = self.provider.models(token)
                    # Sob pressão de memória não utiliza o modelo grande escolhido manualmente.
                    selected = None if mode != requested else model
                    selected = selected or self.provider.choose_model(installed, mode)
                    if not selected or selected not in installed:
                        raise OllamaError('Modelo ausente. Consulte Coach IA para escolher ou baixar um modelo.')
                    facts = dict(analysis_id=analysis.decision.id, pot=analysis.decision.pot,
                                 call=analysis.decision.call, price_percent=analysis.price_percent)
                    prompt = dict(facts=facts, analysis=analysis.model_dump(), focus=focus,
                                  approved_lessons=catalog,
                                  task='Selecione de 1 a 5 lesson_ids para ensinar em português. '
                                       'Repita os facts exatamente. Não calcule probabilidades. '
                                       'Retorne somente o JSON do schema; inclua limits.')
                    messages = [dict(role='system', content='Você organiza explicações didáticas de poker simulado. '
                                     'Não sabe o resultado futuro nem cartas escondidas. /no_think'),
                                dict(role='user', content=json.dumps(prompt, ensure_ascii=False))]
                    try:
                        raw = self.provider.chat(selected, messages, LessonChoice.model_json_schema(), token, progress, cpu)
                    except OllamaError as exc:
                        if cpu or not any(word in str(exc).lower() for word in ('memory', 'cuda', 'gpu')):
                            raise
                        token.check()
                        raw = self.provider.chat(selected, messages, LessonChoice.model_json_schema(), token, progress, True)
                    choice = LessonChoice.model_validate_json(raw)
                    if any(getattr(choice, key) != value for key, value in facts.items()):
                        raise ValueError('A IA alterou dados matemáticos ou a identificação da decisão.')
                    if len(set(choice.lesson_ids)) != len(choice.lesson_ids):
                        raise ValueError('A IA repetiu explicações.')
                    order = list(dict.fromkeys([focus, *choice.lesson_ids, 'limits']))
                    source, actual_model = 'ollama', selected
            except (OllamaError, ValueError) as exc:
                reason = 'IA indisponível ou resposta inconsistente; usei explicação verificada. ' + str(exc)
        token.check()
        text = '\n\n'.join(catalog[key] for key in order)
        return CoachReply(analysis_id=analysis.decision.id, source=source, text=text,
                          reason=reason, model=actual_model)


def review_summary(records):
    if not records:
        return 'Esta mão não tem decisões estruturadas registradas. Os históricos antigos continuam disponíveis.'
    counts = Counter(r.action for r in records)
    paid = sum(r.analysis.decision.call > 0 for r in records)
    text = (f'Você tomou {len(records)} decisões. Em {paid} delas havia um preço para continuar.\n\n'
            'Temas para revisar: preço de pagar, diferença entre pagar e aumentar, e ordem de agir.\n'
            'Escolha cada decisão para estudar somente as cartas e valores disponíveis naquele momento.\n\n')
    if counts['all-in']:
        text += 'Você usou todas as fichas: revise quanto estava em risco e a possibilidade de potes separados.\n\n'
    return text + ('Este resumo identifica situações para estudar; não dá nota nem classifica jogadas como erros '
                   'sem conhecer as mãos possíveis dos adversários. O resultado final não entra na explicação de cada decisão.')
