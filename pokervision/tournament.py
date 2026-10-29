"""Sit & Go de mesa única, independente de Qt e de serviços de IA."""
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
from uuid import uuid4
from pydantic import BaseModel,ConfigDict,Field,model_validator
from .engine import Table


class TournamentConfig(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    players: int = Field(default=6,ge=2,le=9)
    starting_stack: int = Field(default=1000,ge=10,le=1000000)
    initial_big: int = Field(default=20,ge=2,le=100000)
    hands_per_level: int = Field(default=5,ge=1,le=100)
    payouts: tuple[int,...] = (60,40)
    seed: int | None = None

    @model_validator(mode='after')
    def valid(self):
        if not 1<=len(self.payouts)<=self.players or any(type(v) is not int or v<0 for v in self.payouts):
            raise ValueError('Premiação inválida')
        if not sum(self.payouts) or any(a<b for a,b in zip(self.payouts,self.payouts[1:])):
            raise ValueError('Os prêmios devem ser não crescentes e somar um valor positivo')
        if self.initial_big>self.starting_stack:
            raise ValueError('A aposta maior inicial não pode superar o stack inicial')
        return self


def allocate_prizes(pool,weights):
    if type(pool) is not int or pool<1 or not weights or any(type(w) is not int or w<0 for w in weights) or not sum(weights):
        raise ValueError('Fundo e pesos inválidos')
    total=sum(weights)
    values=[pool*w//total for w in weights]
    remainder=pool-sum(values)
    order=sorted(range(len(weights)),key=lambda i:(-(pool*weights[i]%total),i))
    for i in order[:remainder]:
        values[i]+=1
    return tuple(values)


def icm_values(stacks,payouts):
    """ICM exato por subconjuntos: probabilidade do próximo colocado proporcional às fichas.

    Não considera habilidade, posição, próximos blinds, acordos ou bounties.
    """
    stacks=tuple(stacks)
    payouts=tuple(payouts)
    if not 1<=len(stacks)<=9 or any(type(s) is not int or s<=0 for s in stacks):
        raise ValueError('ICM exige de um a nove stacks inteiros positivos')
    if len(payouts)>len(stacks) or any(p<0 for p in payouts) or any(a<b for a,b in zip(payouts,payouts[1:])):
        raise ValueError('Premiação incompatível com ICM')
    n=len(stacks)
    @lru_cache(None)
    def remaining(mask,place):
        if place>=len(payouts) or not mask:
            return (0.,)*n
        total=sum(stacks[i] for i in range(n) if mask&(1<<i))
        values=[0.]*n
        for i in range(n):
            if mask&(1<<i):
                probability=stacks[i]/total
                values[i]+=probability*payouts[place]
                later=remaining(mask^(1<<i),place+1)
                for j in range(n):
                    values[j]+=probability*later[j]
        return tuple(values)
    return remaining((1<<n)-1,0)


class Tournament:
    def __init__(self,config=None,names=None,hero=0,tournament_id=None):
        self.config=config or TournamentConfig()
        names=names or ['Você','Atlas','Luna','Nilo','Íris','Theo','Sol','Gaia','Caio'][:self.config.players]
        if len(names)!=self.config.players or not 0<=hero<len(names):
            raise ValueError('Participantes ou assento inválidos')
        self.id=tournament_id or uuid4().hex
        self.hero=hero
        self.table=Table(names,[self.config.starting_stack]*len(names),
                         small=max(1,self.config.initial_big//2),big=self.config.initial_big,seed=self.config.seed)
        self.total_chips=self.config.starting_stack*self.config.players
        self.remaining=set(range(len(names)))
        self.groups=[]
        self.completed_hands=0
        self.state='ready'
        self.session_id=None

    @property
    def active(self):
        return self.state in ('ready','running')

    @property
    def level(self):
        return self.completed_hands//self.config.hands_per_level+1

    @property
    def next_blinds(self):
        big=min(self.total_chips*2,self.config.initial_big*2**min(self.level-1,30))
        return max(1,big//2),big

    @property
    def phase(self):
        n=len(self.remaining)
        paid=sum(p>0 for p in self.config.payouts)
        if self.state=='completed':
            return 'Encerrado'
        if n==2:
            return 'Duelo final (heads-up) — '+('ambos premiados' if paid>=2 else 'só o campeão é premiado')
        if n<=paid:
            return 'Todos os restantes estão premiados'
        if n==paid+1:
            return 'Bolha: falta uma eliminação para todos os restantes serem premiados'
        return 'Início' if self.completed_hands<self.config.hands_per_level*2 else 'Disputa intermediária'

    def start_hand(self):
        if not self.active or not self.table.finished:
            raise ValueError('Não é possível iniciar outra mão agora')
        self.table.small,self.table.big=self.next_blinds
        self.table.start()
        self.state='running'
        if self.table.finished:
            self.settle_hand()

    def act(self,action,amount=None):
        if not self.active:
            raise ValueError('Torneio encerrado')
        self.table.act(action,amount)
        if self.table.finished:
            self.settle_hand()

    def settle_hand(self):
        if not self.table.finished or self.table.number!=self.completed_hands+1:
            raise ValueError('Mão não concluída ou já processada')
        busted=[i for i in self.remaining if self.table.players[i].stack==0]
        self.remaining.difference_update(busted)
        by_initial=defaultdict(list)
        for i in busted:
            by_initial[self.table.initial_stacks[i]].append(i)
        place=len(self.remaining)+1
        for initial in sorted(by_initial,reverse=True):
            seats=sorted(by_initial[initial])
            self.groups.append(dict(first=place,last=place+len(seats)-1,seats=seats,hand=self.table.number))
            place+=len(seats)
        self.completed_hands+=1
        if len(self.remaining)==1:
            self.groups.append(dict(first=1,last=1,seats=sorted(self.remaining),hand=self.table.number))
            self.state='completed'
        self.assert_integrity()

    def prize_for_group(self,group):
        total=sum(self.config.payouts[p-1] if p<=len(self.config.payouts) else 0
                  for p in range(group['first'],group['last']+1))
        return Fraction(total,len(group['seats']))

    def standings(self):
        result=[]
        for group in sorted(self.groups,key=lambda g:g['first']):
            prize=self.prize_for_group(group)
            for seat in group['seats']:
                result.append(dict(seat=seat,name=self.table.players[seat].name,first=group['first'],last=group['last'],
                    prize_numerator=prize.numerator,prize_denominator=prize.denominator,elimination_hand=group['hand']))
        return result

    def icm(self):
        if not self.table.finished:
            raise ValueError('ICM disponível entre mãos, após a liquidação dos potes')
        seats=sorted(self.remaining)
        stacks=[self.table.players[i].stack for i in seats]
        values=icm_values(stacks,self.config.payouts[:len(seats)])
        return dict(zip(seats,values))

    def abandon(self):
        if not self.table.finished or not self.active:
            raise ValueError('Encerre a mão antes de abandonar o torneio')
        self.state='abandoned'

    def checkpoint(self):
        if not self.table.finished:
            raise ValueError('Checkpoint somente entre mãos')
        return dict(version=1,id=self.id,config=self.config.model_dump(mode='json'),hero=self.hero,state=self.state,
                    session_id=self.session_id,names=[p.name for p in self.table.players],
                    stacks=[p.stack for p in self.table.players],button=self.table.button,
                    remaining=sorted(self.remaining),groups=self.groups,completed_hands=self.completed_hands)

    @classmethod
    def restore(cls,data):
        if data.get('version')!=1 or data.get('state') not in ('ready','running','completed','abandoned'):
            raise ValueError('Checkpoint de torneio incompatível')
        obj=cls(TournamentConfig.model_validate(data['config']),data['names'],data['hero'],data['id'])
        if len(data['stacks'])!=obj.config.players or any(type(s) is not int or s<0 for s in data['stacks']):
            raise ValueError('Stacks inválidos no checkpoint')
        for p,stack in zip(obj.table.players,data['stacks']):
            p.stack=stack
        obj.remaining=set(data['remaining'])
        obj.groups=data['groups']
        obj.completed_hands=data['completed_hands']
        obj.state=data['state']
        obj.session_id=data['session_id']
        obj.table.button=data['button']
        obj.table.number=obj.completed_hands
        previous_level=max(0,(obj.completed_hands-1)//obj.config.hands_per_level)
        obj.table.big=min(obj.total_chips*2,obj.config.initial_big*2**min(previous_level,30))
        obj.table.small=max(1,obj.table.big//2)
        obj.assert_integrity()
        return obj

    def assert_integrity(self):
        if type(self.completed_hands) is not int or self.completed_hands<0 or not -1<=self.table.button<self.config.players:
            raise ValueError('Número de mão ou botão inválidos')
        for group in self.groups:
            if not 1<=group['first']<=group['last']<=self.config.players or group['last']-group['first']+1!=len(group['seats']):
                raise ValueError('Grupo de classificação inválido')
            if group['first']==1 and (self.state!='completed' or set(group['seats'])!=self.remaining):
                raise ValueError('Campeão incompatível com o estado')
        if sum(p.stack for p in self.table.players)!=self.total_chips:
            raise ValueError('Conservação das fichas violada')
        if self.remaining!={i for i,p in enumerate(self.table.players) if p.stack>0}:
            raise ValueError('Lista de participantes inconsistente')
        eliminated=[i for g in self.groups if g['first']!=1 for i in g['seats']]
        if len(eliminated)!=len(set(eliminated)) or set(eliminated)&self.remaining or set(eliminated)|self.remaining!=set(range(self.config.players)):
            raise ValueError('Classificação inconsistente')
        occupied=[p for g in self.groups if g['first']!=1 for p in range(g['first'],g['last']+1)]
        if sorted(occupied)!=list(range(len(self.remaining)+1,self.config.players+1)):
            raise ValueError('Posições inválidas na classificação')
        if self.state=='completed':
            if len(self.remaining)!=1 or len(self.standings())!=self.config.players:
                raise ValueError('Campeão ou classificação ausente')
            paid=sum((Fraction(r['prize_numerator'],r['prize_denominator']) for r in self.standings()),Fraction())
            if paid!=sum(self.config.payouts):
                raise ValueError('Premiação não conservada')
