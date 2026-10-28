"""Avaliador portável: tuplas ordenáveis, maior é melhor; sem dependências nativas."""
from collections import Counter
from itertools import combinations
from random import Random

RANKS = "23456789TJQKA"
SUITS = "cdhs"
DECK = tuple(r + s for r in RANKS for s in SUITS)
LABELS = ("Carta alta", "Par", "Dois pares", "Trinca", "Sequência", "Flush",
          "Full house", "Quadra", "Straight flush")


def validate(cards):
    if len(cards) != len(set(cards)) or any(c not in DECK for c in cards):
        raise ValueError("Cartas inválidas ou duplicadas")


def deck(seed=None):
    cards = list(DECK)
    Random(seed).shuffle(cards)
    return cards


def five(cards):
    values = [RANKS.index(c[0]) + 2 for c in cards]
    counts = Counter(values)
    groups = sorted(((n, v) for v, n in counts.items()), reverse=True)
    unique = sorted(counts, reverse=True)
    straight = (5 if unique == [14, 5, 4, 3, 2] else
                unique[0] if len(unique) == 5 and unique[0] - unique[-1] == 4 else 0)
    flush = len({c[1] for c in cards}) == 1
    if straight and flush:
        return (8, straight)
    if groups[0][0] == 4:
        return (7, groups[0][1], groups[1][1])
    if [g[0] for g in groups] == [3, 2]:
        return (6, groups[0][1], groups[1][1])
    if flush:
        return (5, *sorted(values, reverse=True))
    if straight:
        return (4, straight)
    if groups[0][0] == 3:
        return (3, *(v for n, v in groups))
    if [g[0] for g in groups[:2]] == [2, 2]:
        return (2, groups[0][1], groups[1][1], groups[2][1])
    if groups[0][0] == 2:
        return (1, *(v for n, v in groups))
    return (0, *sorted(values, reverse=True))


def evaluate(cards):
    validate(cards)
    if not 5 <= len(cards) <= 7:
        raise ValueError("Avaliação exige de cinco a sete cartas")
    return max(five(c) for c in combinations(cards, 5))
