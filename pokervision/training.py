"""Exercícios verificáveis, correção independente do LLM e métricas por assunto."""
from itertools import combinations
from collections import Counter
from math import sqrt
from random import Random
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .cards import DECK, RANKS, evaluate, five, LABELS, validate
from .education import cards_text
from .math_engine import pot_odds
from .ranges import hand_class,RESTRICTED,INTERMEDIATE

Topic = Literal['combinations','price','actions','position','ranges','preflop','blinds','draws']
TOPICS = {'combinations':'Combinações vencedoras', 'price':'Preço para continuar',
          'actions':'Apostas e botões', 'position':'Ordem de jogar', 'ranges':'Mãos iniciais e conjuntos', 'preflop':'Situações antes das cartas da mesa',
          'blinds':'Responder à aposta na posição obrigatória maior', 'draws':'Possibilidades de completar um flush'}


class Choice(BaseModel):
    model_config = ConfigDict(frozen=True,extra='forbid')
    key: str
    label: str


class Exercise(BaseModel):
    model_config = ConfigDict(frozen=True,extra='forbid')
    id: str = Field(default_factory=lambda:uuid4().hex)
    topic: Topic
    prompt: str
    choices: tuple[Choice,...]
    answer: str
    steps: tuple[str,...]
    hole: tuple[str,...] = ()
    villain: tuple[str,...] = ()
    board: tuple[str,...] = ()
    source_decision_id: str | None = None

    @model_validator(mode='after')
    def valid(self):
        keys = [c.key for c in self.choices]
        if len(keys)<2 or len(keys)!=len(set(keys)) or self.answer not in keys:
            raise ValueError('Exercício sem resposta única válida')
        validate(list(self.hole+self.villain+self.board))
        if len(self.hole) not in (0,2) or len(self.villain) not in (0,2) or len(self.board) not in (0,3,4,5):
            raise ValueError('Quantidade de cartas incompatível com o exercício')
        return self


class Correction(BaseModel):
    correct: bool
    chosen: str
    expected: str
    explanation: str


def correct(exercise, choice):
    labels = {c.key:c.label for c in exercise.choices}
    if choice not in labels:
        raise ValueError('Escolha uma das respostas apresentadas')
    return Correction(correct=choice==exercise.answer, chosen=labels[choice],
                      expected=labels[exercise.answer], explanation='\n\n'.join(exercise.steps))


def best_five(cards):
    selected=max(combinations(cards,5),key=five)
    score=five(selected)
    def rank(c):
        value=RANKS.index(c[0])+2
        return 1 if value==14 and score[0] in (4,8) and score[1]==5 else value
    if score[0] in (4,8):
        return tuple(sorted(selected,key=rank))
    counts=Counter(c[0] for c in selected)
    return tuple(sorted(selected,key=lambda c:(counts[c[0]],rank(c)),reverse=True))


class ExerciseFactory:
    def __init__(self, seed=None):
        self.rng = Random(seed)

    def _exercise(self, topic, prompt, answers, answer, steps, **cards):
        choices = [Choice(key=key,label=label) for key,label in answers]
        self.rng.shuffle(choices)
        return Exercise(topic=topic,prompt=prompt,choices=tuple(choices),answer=answer,steps=tuple(steps),**cards)

    def generate(self, topic):
        if topic=='price':
            pot=self.rng.choice([20,40,60,80,100,120,200])
            return self.price(pot,self.rng.choice([c for c in [5,10,20,30,40] if c<=pot]))
        if topic=='combinations':
            cards = self.rng.sample(DECK,9)
            a,b,board = tuple(cards[:2]),tuple(cards[2:4]),tuple(cards[4:])
            score_a,score_b = evaluate(a+board),evaluate(b+board)
            answer = 'a' if score_a>score_b else 'b' if score_b>score_a else 'tie'
            if answer=='tie':
                why='É empate: as melhores cinco cartas têm a mesma força. Os naipes não desempatam.'
            elif score_a[0]!=score_b[0]:
                winner='primeiro' if answer=='a' else 'segundo'
                stronger=score_a if answer=='a' else score_b
                weaker=score_b if answer=='a' else score_a
                why=f'O {winner} jogador vence: {LABELS[stronger[0]]} supera {LABELS[weaker[0]]} na ordem das combinações.'
            else:
                ra,rb=next((ra,rb) for ra,rb in zip(score_a[1:],score_b[1:]) if ra!=rb)
                names={11:'Valete',12:'Dama',13:'Rei',14:'Ás'}
                why=(f'As combinações são do mesmo tipo. Na comparação dos valores que as formam, '
                     f'o primeiro valor diferente é {names.get(ra,str(ra))} contra {names.get(rb,str(rb))}. O maior vence.')
            return self._exercise(topic,'Com todas as cartas abertas, quem tem a melhor combinação de cinco cartas?',
                [('a','Primeiro jogador'),('b','Segundo jogador'),('tie','Empate: dividem o pote')],answer,
                [f'Cada um pode usar suas duas cartas e as cinco da mesa, escolhendo somente as cinco melhores.',
                 f'Primeiro jogador: {LABELS[score_a[0]]}. Melhor combinação: {cards_text(best_five(a+board))}.',
                 f'Segundo jogador: {LABELS[score_b[0]]}. Melhor combinação: {cards_text(best_five(b+board))}.',
                 why,
                 'Compare primeiro o tipo de combinação. Se for igual, compare os valores mais altos que a formam e depois as cartas de desempate. Os naipes não desempatarão.',
                 'Aqui todas as cartas são conhecidas. Isso permite comparar o resultado; durante uma decisão normal, as cartas escondidas não são conhecidas.'],
                hole=a,villain=b,board=board)
        if topic=='actions':
            posted = self.rng.choice([1,2,4,5,10])
            target = posted+self.rng.choice([2,5,10,20])
            cost=target-posted
            return self._exercise(topic,f'Você já colocou {posted} fichas nesta rodada. A aposta total exigida agora é {target}. Você tem saldo suficiente. Quantas fichas a mais precisa colocar para acompanhar?',
                [('right',f'{cost} fichas'),('total',f'{target} fichas'),('sum',f'{target+posted} fichas')],'right',
                [f'A aposta exigida é um total de {target} nesta rodada.',f'Você já colocou {posted}; não paga essas fichas de novo.',
                 f'Faltam {target} − {posted} = {cost} fichas. O botão Pagar acrescentaria apenas essa diferença.',
                 'O campo Total na rodada funciona de outro jeito: nele você escolhe o valor total, incluindo o que já colocou.'])
        if topic=='position':
            heads_up=self.rng.choice([False,True])
            return self._exercise(topic,
                'Com apenas dois jogadores, quem age primeiro antes das cartas da mesa?' if heads_up else
                'Em uma mesa com seis jogadores, todos ainda participando, quem age por último depois das três primeiras cartas da mesa?',
                [('button','Quem está no botão'),('sb','Quem não está no botão e colocou a aposta maior')] if heads_up else
                [('button','Quem está no botão'),('sb','Quem colocou a aposta menor'),('bb','Quem colocou a aposta maior')], 'button',
                ['Com apenas dois jogadores, o botão também coloca a aposta menor e começa antes das cartas da mesa. Depois das cartas, o outro jogador começa.' if heads_up else
                 'Depois de abrir cartas da mesa, começa o primeiro jogador ainda participando à esquerda do botão. O botão fica por último se ainda estiver na mão.',
                 'Posição significa a ordem de agir em relação aos outros, e não só o lugar desenhado na mesa. Agir depois permite observar mais ações.'])
        if topic=='ranges':
            hole=tuple(self.rng.sample(DECK,2))
            expected=hand_class(hole)
            r=expected[:2]
            options=[(expected,expected)]
            candidates = ('AA','KK','QQ') if len(expected)==2 else (r+'s',r+'o','AA','KK','QJs')
            for candidate in candidates:
                if candidate not in [k for k,_ in options] and len(options)<3:
                    options.append((candidate,candidate))
            return self._exercise(topic,f'Como escrevemos {cards_text(hole)} no quadro de mãos iniciais?', options,expected,
                [f'A classe correta é {expected}. A = Ás, K = Rei, Q = Dama, J = Valete e T = 10.',
                 'Duas letras iguais indicam um par. Para valores diferentes, s significa mesmo naipe e o significa naipes diferentes.',
                 'Uma classe agrupa mãos parecidas: AKs inclui Ás e Rei de qualquer um dos quatro naipes, desde que ambos tenham o mesmo naipe.',
                 'Saber a classe não diz sozinho qual ação tomar. A posição, as apostas anteriores e os adversários também mudam a situação.'],hole=hole)
        if topic=='preflop':
            button=self.rng.choice([False,True])
            selection=INTERMEDIATE if button else RESTRICTED
            # Equilibra cenários incluídos e excluídos do conjunto, sem ajustar cartas da mesa jogável.
            included=self.rng.choice([False,True])
            pool=[pair for pair in combinations(DECK,2) if (hand_class(pair) in selection)==included]
            hole=tuple(self.rng.choice(pool))
            label=hand_class(hole)
            example=', '.join(sorted(selection))
            return self._exercise(topic,
                ('Você está no botão' if button else 'Você é o primeiro a agir numa mesa de seis')+
                f', antes das cartas da mesa, com 100 vezes a aposta obrigatória maior em fichas. Ninguém entrou na mão. '
                f'Regra deste treino: aumentar apenas com as classes {example}; desistir das outras. '
                f'Com {cards_text(hole)} ({label}), qual opção segue essa regra? '
                'É um exemplo didático, não uma recomendação ótima para toda partida.',
                [('raise','Aumentar segundo a regra do treino'),('fold','Desistir segundo a regra do treino'),
                 ('certainty','Apostar tudo porque a vitória está garantida')], 'raise' if included else 'fold',
                [f'A classe da sua mão é {label}. Ela '+('está' if included else 'não está')+' no conjunto explicitamente indicado.',
                 'Neste exercício seguimos uma regra informada, por isso há um gabarito. O conjunto não veio de um solver e não prova qual jogada teria maior valor numa partida.',
                 'Depois que alguém aumenta, a situação muda: não aplique automaticamente um conjunto de primeira aposta para responder a aumentos.',
                 'Estar no botão permite observar mais ações depois das cartas da mesa; ser o primeiro deixa mais adversários para agir. Nenhuma dessas posições garante vitória.'],hole=hole)
        if topic=='blinds':
            big=self.rng.choice([2,4,10])
            small=big//2
            target=big*self.rng.choice([2,3,4])
            cost=target-big
            pot=target+big+small
            hole=tuple(self.rng.sample(DECK,2))
            return self._exercise(topic,
                f'Você colocou a aposta obrigatória maior de {big} fichas. Um adversário aumentou para um total de {target}. '
                f'Todos os outros desistiram; a aposta menor deixou {small} no centro. Há {pot} fichas no pote. '
                'Você tem saldo suficiente. Quanto precisa acrescentar para acompanhar?',
                [('cost',f'{cost} fichas'),('total',f'{target} fichas'),('free','Nada: já pagou a aposta obrigatória')], 'cost',
                [f'O total exigido é {target}. Você já colocou {big}, então faltam {target} − {big} = {cost} fichas.',
                 f'Depois de acompanhar, o pote seria {pot+cost}. O preço simplificado é {cost} ÷ {pot+cost} = {pot_odds(pot,cost):.1%}, sem taxas ou apostas futuras.',
                 'Ter colocado a aposta obrigatória não obriga você a continuar. Ela já está no pote; a nova decisão é se vale colocar as fichas que faltam.',
                 'O enunciado pergunta o custo, não se pagar é a melhor decisão. Para julgar isso faltam hipóteses sobre a mão adversária e as apostas futuras.'],hole=hole)
        if topic=='draws':
            suit=self.rng.choice('cdhs')
            other=next(s for s in 'cdhs' if s!=suit)
            hole=('A'+suit,'K'+suit)
            board=('Q'+suit,'7'+suit,'2'+other)
            return self._exercise(topic,
                'Você tem quatro cartas do mesmo naipe entre suas cartas e as três cartas da mesa. '
                'Nenhuma carta dos adversários é conhecida. Quantas das 47 cartas desconhecidas completariam cinco desse naipe na próxima carta?',
                [('nine','9 cartas'),('four','4 cartas'),('thirteen','13 cartas')], 'nine',
                ['Cada naipe tem 13 cartas. Você já conhece quatro desse naipe, então restam 13 − 4 = 9.',
                 'Há 52 − 5 = 47 cartas desconhecidas; as cartas escondidas dos outros jogadores fazem parte do que você não conhece.',
                 f'A chance de completar o naipe na próxima carta é 9 ÷ 47 = {9/47:.1%}. A pergunta trata só da próxima carta, não das duas restantes.',
                 'Completar um flush significa ter cinco cartas do mesmo naipe. Ainda pode perder para uma combinação maior: chance de completar não é chance de vencer nem equity.'],hole=hole,board=board)
        raise ValueError('Assunto desconhecido')

    def price(self, pot, call, source_decision_id=None):
        if pot<=0 or call<=0 or call>pot:
            raise ValueError('O exercício exige pote e pagamento positivos, com o pagamento não maior que o pote atual')
        percent=round(pot_odds(pot,call)*100,1)
        values=[percent]
        for candidate in [round(call/pot*100,1),round(percent/2,1),round((percent+20)%100,1),0.,100.]:
            if 0<=candidate<=100 and candidate not in values and len(values)<3:
                values.append(candidate)
        return self._exercise('price',
            f'Há {pot} fichas no centro e custa {call} acompanhar. Sem novas apostas ou taxa, qual é o preço de pagar, em porcentagem do pote após o pagamento?',
            [(str(i),f'{v:g}%') for i,v in enumerate(values)],'0',
            [f'Depois de pagar, haverá {pot} + {call} = {pot+call} fichas em disputa.',
             f'Divida o que você precisa acrescentar pelo pote depois de pagar: {call} ÷ {pot+call}.',
             f'Multiplique por 100: aproximadamente {percent:g}%. Esse é o preço para continuar, não sua chance de ganhar.',
             'A conta supõe que não haverá novas apostas nem retirada de taxa. Não decide sozinha se pagar é uma boa escolha.'],
             source_decision_id=source_decision_id)


def wilson_interval(correct_count, total):
    if type(correct_count) is not int or type(total) is not int or not 0<=correct_count<=total:
        raise ValueError('Informe contagens inteiras válidas de acertos e respostas')
    if total==0:
        return None
    z=1.96
    p=correct_count/total
    denom=1+z*z/total
    center=(p+z*z/(2*total))/denom
    half=z*sqrt((p*(1-p)+z*z/(4*total))/total)/denom
    return max(0,center-half),min(1,center+half)


def topic_progress(attempts):
    result={key:dict(total=0,correct=0,recent_total=0,recent_correct=0,interval=None) for key in TOPICS}
    # Attempts are chronological; only the latest twenty per topic drive recommendation.
    for topic in TOPICS:
        rows=[a for a in attempts if a['topic']==topic]
        recent=rows[-20:]
        total=len(rows)
        ncorrect=sum(bool(a['correct']) for a in rows)
        result[topic]=dict(total=total,correct=ncorrect,recent_total=len(recent),
                           recent_correct=sum(bool(a['correct']) for a in recent),
                           interval=wilson_interval(ncorrect,total))
    return result


def recommend_topic(progress):
    under_sampled=[key for key in TOPICS if progress[key]['total']<3]
    if under_sampled:
        return min(under_sampled,key=lambda k:progress[k]['total'])
    return min(TOPICS,key=lambda k:(progress[k]['recent_correct']+1)/(progress[k]['recent_total']+2))
