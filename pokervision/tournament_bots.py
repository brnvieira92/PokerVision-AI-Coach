"""Adversários de torneio: heurística simples para stacks curtos, sem solver ICM."""
from .bots import Bot
from .cards import RANKS


class TournamentBot(Bot):
    def decide_tournament(self,obs,big_blind):
        if not obs.board and obs.stack<=10*big_blind:
            ranks=sorted((RANKS.index(c[0])+2 for c in obs.hole),reverse=True)
            pair=ranks[0]==ranks[1]
            suited=obs.hole[0][1]==obs.hole[1][1]
            strong=pair or (ranks[0]==14 and ranks[1]>=8) or sum(ranks)>=24 or (suited and sum(ranks)>=22)
            if strong and obs.legal['all_in']:
                return 'all-in',None
            if obs.legal['check']:
                return 'check',None
            return 'fold',None
        return self.decide(obs)
