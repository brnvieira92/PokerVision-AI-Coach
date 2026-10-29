"""Classes de mãos e conjuntos didáticos explícitos; não são ranges GTO."""
from .cards import RANKS, validate

DESC = RANKS[::-1]


def hand_class(cards):
    validate(cards)
    if len(cards) != 2:
        raise ValueError('Informe exatamente duas cartas')
    a,b = sorted(cards, key=lambda c:RANKS.index(c[0]), reverse=True)
    if a[0] == b[0]:
        return a[0]+b[0]
    return a[0]+b[0]+('s' if a[1] == b[1] else 'o')


def matrix_class(row, col):
    if not 0 <= row < 13 or not 0 <= col < 13:
        raise ValueError('Linha e coluna precisam estar entre 0 e 12')
    if row == col:
        return DESC[row]*2
    return DESC[min(row,col)]+DESC[max(row,col)]+('s' if row < col else 'o')


ALL_CLASSES = frozenset(matrix_class(r,c) for r in range(13) for c in range(13))


def combo_count(classes):
    if not set(classes) <= ALL_CLASSES:
        raise ValueError('Classe de mão inválida')
    return sum(6 if len(c)==2 else 4 if c.endswith('s') else 12 for c in set(classes))


# Exemplos próprios, com inclusão de 100% das combinações das classes indicadas.
# Servem para entender conjuntos e sua ampliação; não indicam uma ação ótima.
RESTRICTED = frozenset({'AA','KK','QQ','JJ','TT','AKs','AQs','AKo'})
INTERMEDIATE = RESTRICTED | {'99','88','77','AJs','ATs','KQs','KJs','QJs','AQo'}
WIDER = INTERMEDIATE | {'66','55','44','33','22','A9s','A8s','A7s','A6s','A5s',
                         'A4s','A3s','A2s','KTs','QTs','JTs','T9s','98s','AJo','ATo','KQo'}
PRESETS = {'Exemplo restrito': RESTRICTED, 'Exemplo intermediário': INTERMEDIATE,
           'Exemplo amplo': WIDER, 'Seu conjunto (clique para editar)': frozenset()}
POSITION_GUIDE = {
    'UTG — primeiro a agir antes das cartas da mesa':
        'Numa mesa com seis jogadores, você começa antes das cartas da mesa e ainda há cinco pessoas para agir. '
        'Uma seleção inicial mais restrita é um exemplo de como considerar esse número de adversários.',
    'HJ — segundo a agir antes das cartas da mesa':
        'Nesta mesa, age depois do primeiro jogador e antes de outros quatro. Observe se alguém já apostou; '
        'um conjunto pensado para começar as apostas não serve automaticamente para enfrentar um aumento.',
    'CO — imediatamente antes do botão':
        'Há menos jogadores para agir depois de você antes das cartas da mesa. '
        'Isso ajuda a entender por que a seleção de mãos pode mudar com a posição.',
    'BTN — botão':
        'Com todos ainda participando, o botão age por último depois de abrir as cartas da mesa. '
        'Pode observar o que os outros fizeram antes de decidir. No pré-flop, as apostas obrigatórias ainda agem depois dele.',
    'SB — aposta obrigatória menor':
        'Com três ou mais participantes, é o primeiro a agir depois de abrir as cartas da mesa, se ainda estiver na mão. '
        'Com apenas dois jogadores, o botão também coloca a aposta menor e age primeiro antes das cartas, mas depois do outro jogador nas etapas seguintes.',
    'BB — aposta obrigatória maior':
        'Sem aumento antes de sua vez, pode passar se sua aposta obrigatória já cobriu o valor exigido. '
        'Se todos os outros desistirem, recebe as fichas sem precisar abrir as cartas. '
        'Defender essa aposta contra um aumento é uma situação diferente de ser o primeiro a apostar.'}
