"""Bots heurísticos recebem apenas observação pública e a própria mão."""
from dataclasses import dataclass
from random import Random
from .cards import RANKS, evaluate


@dataclass(frozen=True)
class Observation:
    hole: tuple
    board: tuple
    stack: int
    pot: int
    position: int
    opponents: int
    history: tuple
    legal: dict


def observe(table):
    i = table.actor
    p = table.players[i]
    return Observation(tuple(p.hole), tuple(table.board), p.stack, table.pot,
                       (i-table.button) % len(table.players), len(table._live())-1,
                       tuple(table.history), dict(table.legal()))


class Bot:
    def __init__(self, profile='TAG', seed=None):
        self.profile, self.rng = profile, Random(seed)

    def decide(self, obs):
        ranks = sorted((RANKS.index(c[0])+2 for c in obs.hole), reverse=True)
        strength = (sum(ranks)/28 + (0.32 if ranks[0] == ranks[1] else 0) +
                    (0.07 if obs.hole[0][1] == obs.hole[1][1] else 0))
        if obs.board:
            category = evaluate(list(obs.hole + obs.board))[0]
            strength = min(1, 0.18 + category * 0.16 + max(ranks)/100)
        loose = self.profile in ('LAG', 'Loose passive', 'Recreativo')
        passive = self.profile in ('Tight passive', 'Loose passive', 'Conservador')
        late_position = obs.position == 0 or obs.position >= 4
        strength += 0.04 if late_position and not obs.board else 0
        strength -= max(0, obs.opponents - 1) * 0.015
        threshold = 0.70 if loose else 0.83
        l = obs.legal
        pressure = l['call'] / max(1, obs.pot + l['call'])
        # Mistura limitada por força, posição e preço; não é um solver GTO.
        aggression = strength > threshold and self.rng.random() < (0.18 if passive else 0.55)
        if aggression and l['raise_allowed']:
            target = min(l['maximum'], max(l['minimum'], int(obs.pot * 0.65)))
            return 'raise', target
        if l['check']:
            return 'check', None
        if strength > (0.40 if loose else 0.54) + pressure * 0.5:
            return 'call', None
        return 'fold', None
