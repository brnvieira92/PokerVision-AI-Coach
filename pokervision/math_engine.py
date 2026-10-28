"""Matemática independente da explicação textual e dos adversários."""
from math import sqrt
from random import Random
from pydantic import BaseModel, Field
from .cards import DECK, validate, evaluate


class EquityResult(BaseModel):
    equity: float = Field(ge=0, le=1)
    samples: int = Field(gt=0)
    standard_error: float = Field(ge=0)
    assumption: str = 'Adversários com mãos uniformes; sem modelar folds ou apostas futuras.'


def pot_odds(pot, call):
    if pot < 0 or call < 0:
        raise ValueError('Pote e call não podem ser negativos')
    return call / (pot + call) if pot + call else 0.0


def spr(stack, pot):
    if stack < 0 or pot <= 0:
        raise ValueError('SPR exige stack não negativo e pote positivo')
    return stack / pot


def call_ev(equity, pot, call):
    if not 0 <= equity <= 1 or pot < 0 or call < 0:
        raise ValueError('Hipóteses inválidas')
    return equity * pot - (1 - equity) * call


def estimate_equity(hole, board=(), opponents=1, samples=300, seed=None):
    known = list(hole) + list(board)
    validate(known)
    if len(hole) != 2 or len(board) > 5 or not 1 <= opponents <= 8 or samples <= 0:
        raise ValueError('Cenário inválido')
    remaining = [c for c in DECK if c not in known]
    rng, results = Random(seed), []
    for _ in range(samples):
        draw = rng.sample(remaining, 5 - len(board) + 2 * opponents)
        community = list(board) + draw[:5-len(board)]
        offset = 5 - len(board)
        scores = [evaluate(list(hole) + community)] + [
            evaluate(draw[offset+2*i:offset+2*i+2] + community) for i in range(opponents)]
        best = max(scores)
        results.append(1 / scores.count(best) if scores[0] == best else 0)
    mean = sum(results) / samples
    error = sqrt(sum((v-mean)**2 for v in results) / (samples-1) / samples) if samples > 1 else 0
    return EquityResult(equity=mean, samples=samples, standard_error=error)
