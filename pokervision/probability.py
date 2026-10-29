"""Laboratório Monte Carlo: equity e melhoria de categoria são eventos distintos."""
from collections import Counter
from math import sqrt,log
from random import Random
from pydantic import BaseModel, Field, model_validator, ConfigDict
from .cards import DECK, validate, evaluate, LABELS
from .ranges import hand_class, ALL_CLASSES
from .resources import CancelToken


class RunoutExample(BaseModel):
    board: tuple[str,...]
    opponent: tuple[str,str]
    outcome: str
    improved: bool | None


class SimulationResult(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    samples: int = Field(ge=2)
    wins: int = Field(ge=0)
    ties: int = Field(ge=0)
    losses: int = Field(ge=0)
    equity: float = Field(ge=0,le=1)
    standard_error: float = Field(ge=0)
    interval: tuple[float,float]
    improved_category: int | None = Field(default=None,ge=0)
    initial_category: str | None = None
    categories: dict[str,int]
    examples: tuple[RunoutExample,...]
    assumption: str
    seed: int

    @model_validator(mode='after')
    def verify(self):
        if self.wins+self.ties+self.losses!=self.samples or sum(self.categories.values())!=self.samples:
            raise ValueError('Contagens incompatíveis')
        if abs(self.equity-(self.wins+self.ties/2)/self.samples)>1e-9:
            raise ValueError('Equity incompatível com vitórias e empates')
        if not 0<=self.interval[0]<=self.equity<=self.interval[1]<=1:
            raise ValueError('Faixa de amostragem inválida')
        if self.improved_category is not None and self.improved_category>self.samples:
            raise ValueError('Contagem de melhoria inválida')
        return self


def expand_range(classes, blocked=()):
    from itertools import combinations
    validate(list(blocked))
    if not set(classes)<=ALL_CLASSES:
        raise ValueError('Classe de mão inválida no conjunto')
    remaining=[c for c in DECK if c not in blocked]
    return tuple(pair for pair in combinations(remaining,2) if hand_class(pair) in classes)


def simulate(hole, board=(), *, opponent=None, classes=None, samples=600, seed=42,
             token=None, progress=None):
    token=token or CancelToken()
    token.check()
    hole,board=tuple(hole),tuple(board)
    if len(hole)!=2 or len(board) not in (0,3,4,5) or type(samples) is not int or not 2<=samples<=5000:
        raise ValueError('Informe duas cartas próprias, 0/3/4/5 cartas de mesa e de 2 a 5000 simulações')
    if opponent is not None and classes is not None:
        raise ValueError('Escolha uma mão adversária ou um conjunto, não ambos')
    opponent=tuple(opponent) if opponent is not None else None
    if opponent is not None and len(opponent)!=2:
        raise ValueError('O adversário precisa ter duas cartas')
    known=hole+board+(opponent or ())
    validate(list(known))
    available=[c for c in DECK if c not in known]
    candidates=None
    if classes is not None:
        candidates=expand_range(set(classes),hole+board)
        if not candidates:
            raise ValueError('O conjunto não contém combinações possíveis após retirar as cartas conhecidas')
    assumption=('Um adversário com as duas cartas escolhidas; sem apostas futuras.' if opponent else
                f'Um adversário uniforme entre {len(candidates)} combinações legais do conjunto; sem apostas futuras.' if candidates is not None else
                'Um adversário uniforme entre todas as mãos restantes; sem apostas futuras.')
    rng=Random(seed)
    current=evaluate(hole+board)[0] if len(board)>=3 else None
    wins=ties=losses=improved=0
    categories=Counter()
    examples={}
    shares=[]
    for i in range(samples):
        token.check()
        villain=rng.choice(candidates) if candidates is not None else opponent
        if villain is None:
            draw=rng.sample(available,2+5-len(board))
            villain=tuple(draw[:2])
            community=board+tuple(draw[2:])
        else:
            remaining=[c for c in available if c not in villain]
            community=board+tuple(rng.sample(remaining,5-len(board)))
        own_score,other_score=evaluate(hole+community),evaluate(villain+community)
        category_up=own_score[0]>current if current is not None else None
        if category_up:
            improved+=1
        categories[LABELS[own_score[0]]]+=1
        if own_score>other_score:
            wins+=1
            share,outcome=1.,'Vitória'
        elif own_score==other_score:
            ties+=1
            share,outcome=.5,'Empate'
        else:
            losses+=1
            share,outcome=0.,'Derrota'
        shares.append(share)
        key=(outcome,category_up)
        if key not in examples and len(examples)<6:
            examples[key]=RunoutExample(board=community,opponent=villain,outcome=outcome,improved=category_up)
        if progress and ((i+1)%50==0 or i+1==samples):
            progress((i+1,samples))
    equity=sum(shares)/samples
    error=sqrt(sum((v-equity)**2 for v in shares)/(samples-1)/samples)
    return SimulationResult(samples=samples,wins=wins,ties=ties,losses=losses,equity=equity,
        standard_error=error,interval=(max(0,equity-sqrt(log(40)/(2*samples))),
                                     min(1,equity+sqrt(log(40)/(2*samples)))),
        improved_category=improved if current is not None else None,
        initial_category=LABELS[current] if current is not None else None,
        categories=dict(categories),examples=tuple(examples.values()),assumption=assumption,seed=seed)
