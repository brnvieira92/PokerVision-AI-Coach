"""Análise de uma decisão do simulador usando somente dados públicos e cartas próprias.

Hipótese terminal explícita: pagar agora; todos os adversários ainda na mão
acompanham o preço atual até o limite do saldo; ninguém aumenta ou desiste;
as próximas rodadas são passadas até a comparação final.
"""
from math import sqrt,log
from random import Random
from uuid import uuid4
from pydantic import BaseModel,Field,ConfigDict,model_validator
from .cards import DECK,validate,evaluate
from .probability import expand_range
from .resources import CancelToken


class PublicPlayer(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    name: str
    stack: int = Field(ge=0)
    bet: int = Field(ge=0)
    invested: int = Field(ge=0)
    folded: bool


class AssistedScenario(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    id: str = Field(default_factory=lambda:uuid4().hex)
    hand: int = Field(ge=1)
    street: str
    hero: int = Field(ge=0)
    button: int = Field(ge=0)
    hole: tuple[str,str]
    board: tuple[str,...]
    current_bet: int = Field(ge=0)
    call: int = Field(ge=0)
    players: tuple[PublicPlayer,...] = Field(min_length=2,max_length=9)
    rake_bps: int = Field(ge=0,le=10000)
    rake_cap: int = Field(ge=0)

    @model_validator(mode='after')
    def valid(self):
        validate(list(self.hole+self.board))
        if len(self.board)!={'preflop':0,'flop':3,'turn':4,'river':5}.get(self.street,-1):
            raise ValueError('Etapa e cartas incompatíveis')
        if self.hero>=len(self.players) or self.button>=len(self.players):
            raise ValueError('Assento inválido')
        p=self.players[self.hero]
        if p.folded or p.stack<=0 or sum(not p.folded for p in self.players)<2:
            raise ValueError('Não há decisão atual para estudar')
        if any(p.bet>p.invested or p.bet>self.current_bet for p in self.players):
            raise ValueError('Apostas públicas inválidas')
        if self.call!=min(p.stack,max(0,self.current_bet-p.bet)):
            raise ValueError('Custo incompatível com o preço público')
        return self


def capture(table,hero):
    if table.finished or table.actor!=hero:
        raise ValueError('A ajuda só está disponível na sua vez')
    return AssistedScenario(hand=table.number,street=table.street,hero=hero,button=table.button,
        hole=tuple(table.players[hero].hole),board=tuple(table.board),current_bet=table.current,
        call=table.legal()['call'],rake_bps=table.rake_bps,rake_cap=table.rake_cap,
        players=tuple(PublicPlayer(name=p.name,stack=p.stack,bet=p.bet,invested=p.invested,folded=p.folded)
                      for p in table.players))


class PotProjection(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    gross: int = Field(ge=0)
    net: int = Field(ge=0)
    eligible: tuple[int,...]
    refund_to: int | None = None


def project_pots(scenario):
    amounts=[]
    for i,p in enumerate(scenario.players):
        extra=0 if p.folded else min(p.stack,max(0,scenario.current_bet-p.bet))
        amounts.append(p.invested+extra)
    previous=0
    cap=scenario.rake_cap  # Hipótese termina em showdown, logo o flop será aberto.
    pots=[]
    for level in sorted({a for a in amounts if a}):
        contributors=[i for i,a in enumerate(amounts) if a>=level]
        gross=(level-previous)*len(contributors)
        previous=level
        eligible=tuple(i for i in contributors if not scenario.players[i].folded)
        refund=contributors[0] if len(contributors)==1 else None
        if refund is not None:
            pots.append(PotProjection(gross=gross,net=gross,eligible=(),refund_to=refund))
        else:
            if not eligible:
                raise ValueError('Pote sem participante elegível')
            fee=min(cap,gross*scenario.rake_bps//10000)
            cap-=fee
            pots.append(PotProjection(gross=gross,net=gross-fee,eligible=eligible))
    return tuple(amounts),tuple(pots)


class PotEstimate(BaseModel):
    projection: PotProjection
    hero_average: float = Field(ge=0)
    interval: tuple[float,float]


class BoardPossibility(BaseModel):
    board: tuple[str,...]
    outcome: str
    improved: bool | None


class AssistedResult(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    scenario_id: str
    samples: int = Field(ge=2)
    opponents: int = Field(ge=1,le=8)
    wins: int = Field(ge=0)
    ties: int = Field(ge=0)
    losses: int = Field(ge=0)
    equity: float = Field(ge=0,le=1)
    interval: tuple[float,float]
    improved_category: int | None = Field(default=None,ge=0)
    final_contributions: tuple[int,...]
    pots: tuple[PotEstimate,...]
    expected_award: float = Field(ge=0)
    eligible_pot: int = Field(ge=0)
    refund: int = Field(ge=0)
    examples: tuple[BoardPossibility,...]
    range_description: str
    seed: int

    @model_validator(mode='after')
    def coherent(self):
        if self.wins+self.ties+self.losses!=self.samples:
            raise ValueError('Resultados incompatíveis com amostra')
        if abs(self.expected_award-sum(p.hero_average for p in self.pots))>1e-7:
            raise ValueError('Recebimento incompatível com potes')
        if not 0<=self.interval[0]<=self.equity<=self.interval[1]<=1:
            raise ValueError('Intervalo inválido')
        return self


def award_for_hero(pot,scores,hero,button,seats):
    if pot.refund_to is not None:
        return pot.net if pot.refund_to==hero else 0
    if hero not in pot.eligible:
        return 0
    best=max(scores[i] for i in pot.eligible)
    winners=[i for i in pot.eligible if scores[i]==best]
    if hero not in winners:
        return 0
    ordered=sorted(winners,key=lambda i:(i-button-1)%seats)
    share,odd=divmod(pot.net,len(winners))
    return share+int(ordered.index(hero)<odd)


def simulate_assisted(scenario,*,classes=None,samples=300,seed=42,token=None,progress=None):
    token=token or CancelToken()
    token.check()
    if type(samples) is not int or not 2<=samples<=2000:
        raise ValueError('Use de 2 a 2000 simulações')
    opponents=tuple(i for i,p in enumerate(scenario.players) if i!=scenario.hero and not p.folded)
    available=tuple(c for c in DECK if c not in scenario.hole+scenario.board)
    candidates=expand_range(set(classes),scenario.hole+scenario.board) if classes is not None else None
    if candidates is not None and (not candidates or len({c for pair in candidates for c in pair})<2*len(opponents)):
        raise ValueError('O conjunto é estreito demais para todos os adversários sem repetir cartas. Amplie-o ou escolha mãos aleatórias.')
    description=(f'Todos os {len(opponents)} adversários usam o mesmo conjunto escolhido por você; '
                 'combinações equiprováveis condicionadas a não repetir cartas. Não é um range inferido pelas ações.' if candidates is not None else
                 f'Os {len(opponents)} adversários têm mãos aleatórias, sem repetição de cartas. Não modelamos tendências ou ranges pelas apostas.')
    contributions,pots=project_pots(scenario)
    rng=Random(seed)
    totals=[0.]*len(pots)
    wins=ties=losses=improved=0
    shares=[]
    examples={}
    initial=evaluate(scenario.hole+scenario.board)[0] if len(scenario.board)>=3 else None
    for sample in range(samples):
        token.check()
        if candidates is None:
            draw=rng.sample(available,2*len(opponents)+5-len(scenario.board))
            hands={seat:tuple(draw[2*k:2*k+2]) for k,seat in enumerate(opponents)}
            board=scenario.board+tuple(draw[2*len(opponents):])
        else:
            # Rejeita a atribuição inteira; sortear apenas os pares que faltam enviesaria a distribuição conjunta.
            for attempt in range(2000):
                token.check()
                selected=[rng.choice(candidates) for _ in opponents]
                used=[c for pair in selected for c in pair]
                if len(used)==len(set(used)):
                    break
            else:
                raise ValueError('Não consegui sortear esse conjunto para todos sem colisões. Use um conjunto mais amplo ou mãos aleatórias.')
            hands=dict(zip(opponents,selected))
            remaining=[c for c in available if c not in used]
            board=scenario.board+tuple(rng.sample(remaining,5-len(scenario.board)))
        scores={seat:evaluate(hole+board) for seat,hole in hands.items()}
        scores[scenario.hero]=evaluate(scenario.hole+board)
        best=max(scores.values())
        winners=[i for i,score in scores.items() if score==best]
        if scenario.hero not in winners:
            share,outcome=0.,'Perde contra a melhor mão entre todos'
            losses+=1
        elif len(winners)>1:
            share,outcome=1/len(winners),'Empata com a melhor mão entre todos'
            ties+=1
        else:
            share,outcome=1.,'Vence contra todos'
            wins+=1
        shares.append(share)
        up=scores[scenario.hero][0]>initial if initial is not None else None
        if up:
            improved+=1
        key=(outcome,up)
        if key not in examples and len(examples)<6:
            examples[key]=BoardPossibility(board=board,outcome=outcome,improved=up)
        for k,pot in enumerate(pots):
            totals[k]+=award_for_hero(pot,scores,scenario.hero,scenario.button,len(scenario.players))
        if progress and ((sample+1)%25==0 or sample+1==samples):
            progress((sample+1,samples))
    equity=sum(shares)/samples
    radius=sqrt(log(40)/(2*samples))
    return AssistedResult(scenario_id=scenario.id,samples=samples,opponents=len(opponents),wins=wins,ties=ties,losses=losses,
        equity=equity,interval=(max(0,equity-radius),min(1,equity+radius)),improved_category=improved if initial is not None else None,
        final_contributions=contributions,pots=tuple(PotEstimate(projection=p,hero_average=totals[k]/samples,
            interval=((max(0,totals[k]/samples-radius*p.net),min(p.net,totals[k]/samples+radius*p.net))
                      if scenario.hero in p.eligible else (totals[k]/samples,totals[k]/samples)))
            for k,p in enumerate(pots)),
        expected_award=sum(totals)/samples,eligible_pot=sum(p.net for p in pots if scenario.hero in p.eligible),
        refund=sum(p.net for p in pots if p.refund_to==scenario.hero),examples=tuple(examples.values()),range_description=description,seed=seed)
