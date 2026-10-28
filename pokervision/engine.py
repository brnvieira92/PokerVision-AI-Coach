"""Máquina de estados de no-limit Hold'em, sem qualquer dependência de GUI."""
from dataclasses import dataclass, field
from .cards import deck, evaluate, LABELS


@dataclass
class Player:
    name: str
    stack: int
    hole: list[str] = field(default_factory=list)
    folded: bool = False
    bet: int = 0
    invested: int = 0


class Table:
    def __init__(self, names=None, stacks=None, small=1, big=2, seed=None,
                 rake_bps=0, rake_cap=0):
        names = names or ['Você', 'Atlas', 'Luna', 'Nilo', 'Íris', 'Theo']
        stacks = stacks if stacks is not None else [200] * len(names)
        if not 2 <= len(names) <= 9 or len(stacks) != len(names):
            raise ValueError('Mesa exige de 2 a 9 jogadores')
        if any(type(s) is not int or s < 0 for s in stacks):
            raise ValueError('Stacks devem ser inteiros não negativos')
        if type(small) is not int or type(big) is not int or not 0 < small <= big:
            raise ValueError('Blinds inválidos')
        if not 0 <= rake_bps <= 10000 or rake_cap < 0:
            raise ValueError('Rake inválido')
        self.players = [Player(n, s) for n, s in zip(names, stacks)]
        self.small, self.big, self.seed = small, big, seed
        self.rake_bps, self.rake_cap = rake_bps, rake_cap
        self.button = -1
        self.number = 0
        self.street = 'finished'
        self.actor = None
        self.board, self.history, self.awards = [], [], {}
        self.pots = []
        self.rake = 0

    @property
    def finished(self):
        return self.street == 'finished'

    @property
    def pot(self):
        return sum(p.invested for p in self.players) if not self.finished else 0

    def _next(self, seat, seats):
        return next((i for k in range(1, len(self.players) + 1)
                     if (i := (seat + k) % len(self.players)) in seats), None)

    def _pay(self, seat, amount):
        p = self.players[seat]
        amount = min(amount, p.stack)
        p.stack -= amount
        p.bet += amount
        p.invested += amount

    def start(self):
        if not self.finished:
            raise ValueError('Termine a mão atual')
        active = {i for i, p in enumerate(self.players) if p.stack > 0}
        if len(active) < 2:
            raise ValueError('Recomponha fichas para iniciar outra mão')
        self.number += 1
        self.button = self._next(self.button, active)
        self.cards = deck(None if self.seed is None else self.seed + self.number)
        self.board, self.history, self.awards, self.pots = [], [], {}, []
        self.rake = 0
        self.initial_total = sum(p.stack for p in self.players)
        self.initial_stacks = [p.stack for p in self.players]
        for i, p in enumerate(self.players):
            p.hole = []
            p.bet = p.invested = 0
            p.folded = i not in active
        order = []
        seat = self.button
        for _ in active:
            seat = self._next(seat, active)
            order.append(seat)
        for _ in range(2):
            for i in order:
                self.players[i].hole.append(self.cards.pop())
        self.sb = self.button if len(active) == 2 else self._next(self.button, active)
        self.bb = self._next(self.sb, active)
        self._pay(self.sb, self.small)
        self._pay(self.bb, self.big)
        self.history.extend([f'{self.players[self.sb].name}: small blind {self.players[self.sb].bet}',
                             f'{self.players[self.bb].name}: big blind {self.players[self.bb].bet}'])
        self.street, self.current, self.increment = 'preflop', self.big, self.big
        self.acted = {}
        self.pending = self._able()
        self._advance(self.bb)

    def _live(self):
        return {i for i, p in enumerate(self.players) if not p.folded}

    def _able(self):
        return {i for i in self._live() if self.players[i].stack > 0}

    def legal(self):
        if self.actor is None or self.finished:
            return {}
        p = self.players[self.actor]
        owed = max(0, self.current - p.bet)
        maximum = p.bet + p.stack
        reopened = (self.actor not in self.acted or
                    self.current - self.acted[self.actor] >= self.increment)
        can_raise = reopened and maximum > self.current and len(self._able()) > 1
        return dict(fold=True, check=owed == 0, call=min(owed, p.stack),
                    raise_allowed=can_raise, minimum=self.current + self.increment,
                    maximum=maximum, all_in=maximum <= self.current or can_raise)

    def act(self, action, amount=None):
        legal = self.legal()
        if not legal:
            raise ValueError('Não há jogador para agir')
        seat = self.actor
        p = self.players[seat]
        if action == 'fold':
            p.folded = True
        elif action == 'check' and legal['check']:
            pass
        elif action == 'call' and legal['call'] > 0:
            self._pay(seat, legal['call'])
        elif action in ('raise', 'all-in'):
            target = legal['maximum'] if action == 'all-in' else amount
            if type(target) is not int or target <= p.bet or target > legal['maximum']:
                raise ValueError('Valor inválido; informe o total da aposta na rodada')
            if target <= self.current:
                if action != 'all-in':
                    raise ValueError('Use call para cobrir a aposta')
            elif not legal['raise_allowed'] or (target < legal['minimum'] and target != legal['maximum']):
                raise ValueError('Raise indisponível ou abaixo do mínimo')
            self._pay(seat, target - p.bet)
            if target > self.current:
                delta = target - self.current
                self.current = target
                if delta >= self.increment:
                    self.increment = delta
                self.pending |= {i for i in self._able() if i != seat and self.players[i].bet < target}
        else:
            raise ValueError('Ação ilegal')
        self.history.append(f'{self.street} · {p.name}: {action}' +
                            (f' → {p.bet}' if action in ('raise', 'all-in', 'call') else ''))
        self.acted[seat] = self.current
        self.pending.discard(seat)
        self._advance(seat)
        self.assert_integrity()

    def _advance(self, previous):
        if len(self._live()) == 1:
            self._settle()
            return
        self.pending &= self._able()
        # Um único jogador com fichas só decide se ainda precisa cobrir aposta.
        if len(self._able()) <= 1:
            self.pending = {i for i in self.pending if self.players[i].bet < self.current}
        if self.pending:
            self.actor = self._next(previous, self.pending)
            return
        if self.street == 'river':
            self._settle()
            return
        for p in self.players:
            p.bet = 0
        self.current, self.increment, self.acted = 0, self.big, {}
        self.cards.pop()  # burn
        if self.street == 'preflop':
            self.street = 'flop'
            self.board.extend(self.cards.pop() for _ in range(3))
        else:
            self.street = 'turn' if self.street == 'flop' else 'river'
            self.board.append(self.cards.pop())
        self.history.append(f'{self.street}: {" ".join(self.board)}')
        self.pending = self._able()
        self._advance(self.button)

    def _settle(self):
        live = self._live()
        levels = sorted({p.invested for p in self.players if p.invested})
        previous = 0
        rake_left = self.rake_cap if len(self.board) >= 3 else 0
        for level in levels:
            contributors = {i for i, p in enumerate(self.players) if p.invested >= level}
            amount = (level - previous) * len(contributors)
            previous = level
            eligible = contributors & live
            if len(contributors) == 1:  # devolução de aposta não coberta
                winners = contributors
                fee = 0
            else:
                fee = min(rake_left, amount * self.rake_bps // 10000)
                rake_left -= fee
                if len(live) == 1:
                    winners = live
                else:
                    scores = {i: evaluate(self.players[i].hole + self.board) for i in eligible}
                    best = max(scores.values())
                    winners = {i for i, score in scores.items() if score == best}
            self.rake += fee
            amount -= fee
            self.pots.append({'amount': amount, 'eligible': sorted(eligible), 'winners': sorted(winners)})
            ordered = sorted(winners, key=lambda i: (i - self.button - 1) % len(self.players))
            share, odd = divmod(amount, len(ordered))
            for k, i in enumerate(ordered):
                value = share + (k < odd)
                self.players[i].stack += value
                self.awards[i] = self.awards.get(i, 0) + value
        if len(live) > 1:
            self.history.append('Showdown: ' + ', '.join(
                f'{self.players[i].name}: {LABELS[evaluate(self.players[i].hole + self.board)[0]]}'
                for i in sorted(live)))
        self.street, self.actor = 'finished', None
        self.history.append('Distribuição: ' + ', '.join(f'{self.players[i].name} +{v}' for i, v in self.awards.items()))
        self.assert_integrity()

    def rebuy(self, seat, amount):
        if not self.finished or type(amount) is not int or amount <= 0:
            raise ValueError('Recomposição apenas entre mãos, em fichas inteiras positivas')
        self.players[seat].stack += amount

    def assert_integrity(self):
        assert all(p.stack >= 0 and p.invested >= 0 for p in self.players)
        total = sum(p.stack for p in self.players)
        assert total + (self.rake if self.finished else self.pot) == self.initial_total
        known = self.board + [c for p in self.players for c in p.hole]
        assert len(known) == len(set(known))
