"""Apresentação didática; mantém códigos internos e históricos antigos compatíveis."""
import re
from .cards import DECK
from .math_engine import pot_odds

STAGES = {
    'preflop': 'Antes das cartas da mesa (pré-flop)',
    'flop': 'Primeiras 3 cartas da mesa (flop)',
    'turn': 'Quarta carta da mesa (turn)',
    'river': 'Quinta e última carta da mesa (river)',
    'finished': 'Mão encerrada',
}
RANK_NAMES = {'T': '10', 'J': 'Valete', 'Q': 'Dama', 'K': 'Rei', 'A': 'Ás'}
SUIT_NAMES = {'c': 'paus', 'd': 'ouros', 'h': 'copas', 's': 'espadas'}


def card_name(code):
    if code not in DECK:
        return code
    return f'{RANK_NAMES.get(code[0], code[0])} de {SUIT_NAMES[code[1]]}'


def cards_text(cards):
    return ', '.join(card_name(c) for c in cards) or 'nenhuma carta aberta ainda'


def readable_history(lines):
    """Traduz apenas padrões conhecidos, sem alterar nomes ou o registro original."""
    result = []
    actions = {'fold': 'desistiu desta mão', 'check': 'passou a vez sem apostar',
               'call': 'pagou para acompanhar a aposta', 'raise': 'apostou ou aumentou a aposta',
               'all-in': 'colocou todas as fichas disponíveis'}
    for line in lines:
        action = re.fullmatch(r'(preflop|flop|turn|river) · (.*): (fold|check|call|raise|all-in)(?: → (\d+))?', line)
        blind = re.fullmatch(r'(.*): (small blind|big blind) (\d+)', line)
        board = re.fullmatch(r'(flop|turn|river): (.*)', line)
        if action:
            stage, name, verb, total = action.groups()
            text = f'{STAGES[stage]} — {name} {actions[verb]}.'
            if total is not None:
                text += f' Total já colocado nesta rodada: {total} fichas.'
            result.append(text)
        elif blind:
            name, kind, value = blind.groups()
            size = 'menor' if kind == 'small blind' else 'maior'
            result.append(f'{name} colocou a aposta obrigatória {size}: {value} fichas.')
        elif board:
            stage, cards = board.groups()
            result.append(f'{STAGES[stage]} — Cartas abertas: {cards_text(cards.split())}.')
        elif line.startswith('Showdown: '):
            result.append('Comparação final das melhores combinações de 5 cartas: ' + line[10:])
        elif line.startswith('Distribuição: '):
            awards = re.sub(r' \+(\d+)', r' recebeu \1 fichas', line[len('Distribuição: '):])
            result.append('Entrega das fichas (inclui possíveis devoluções): ' + awards)
        else:
            result.append(line)
    return '\n\n'.join(result)


def turn_lesson(table, hero):
    p = table.players[hero]
    legal = table.legal()
    cost = legal['call']
    text = (f'No centro: {table.pot} fichas. Esse conjunto de fichas se chama pote.\n'
            f'Seu saldo para apostar: {p.stack} fichas.\n\n')
    if not cost:
        return text + ('Você pode passar a vez sem pagar (check). Apostar coloca mais fichas em disputa. '
                       'Não é necessário pagar nada para continuar neste momento.\n\n'
                       'Use “Entender os termos” para consultar exemplos e o significado dos botões.')
    text += f'Para continuar, pague mais {cost} fichas. O botão Pagar faz isso.\n\n'
    short_or_sidepot = (cost < max(0, table.current-p.bet) or
                       any(not other.folded and other.stack == 0 for other in table.players))
    if short_or_sidepot:
        text += ('Há uma aposta com todas as fichas. Podem existir grupos de fichas disputados por jogadores diferentes '
                 '(potes separados). Por isso, não mostro a conta simples que usa o pote inteiro.\n\n')
    else:
        final_pot = table.pot + cost
        percent = pot_odds(table.pot, cost)*100
        text += (f'Entenda o preço: pagando {cost}, haverá {final_pot} fichas em disputa.\n'
                 f'A conta é {cost} ÷ {final_pot} = {percent:.1f}%.\n'
                 f'Em situações iguais repetidas, seria preciso recuperar em média pelo menos {percent:.1f}% '
                 'desse pote para compensar esse pagamento. Se não houvesse empates, isso equivaleria a vencer '
                 f'cerca de {percent:.1f} em cada 100 vezes.\n\n'
                 'Essa conta explica o preço de continuar; ela NÃO mede a força das suas cartas. '
                 'Para simplificar, supõe que ninguém apostará mais depois e que nenhuma taxa será retirada do pote. '
                 'Se isso mudar, a conta também muda.\n\n')
    return text + ('Desistir encerra sua participação; as fichas que você já apostou ficam no centro.\n\n'
                   f'Suas cartas: {cards_text(p.hole)}. {STAGES[table.street]}.\n\n'
                   'Consulte “Entender os termos” para ver exemplos e as regras básicas.')


GLOSSARY = '''
<h2>Poker explicado do começo</h2>
<p>Use este guia enquanto pratica. Todas as fichas deste aplicativo são fictícias.</p>
<h3>Pote (pot)</h3>
<p>É a soma das fichas colocadas no centro durante uma mão. Exemplo: se três jogadores colocam 10 fichas cada, o pote tem 30. Ele será entregue ao vencedor ou dividido em caso de empate.</p>
<h3>Fichas disponíveis (stack)</h3>
<p>É o que cada jogador ainda tem para apostar. As fichas já colocadas no pote deixaram de fazer parte desse saldo.</p>
<h3>Os botões</h3>
<p><b>Desistir (fold):</b> você deixa de disputar esta mão. As fichas que já apostou ficam no pote.</p>
<p><b>Passar (check):</b> você continua sem pagar, quando não há aposta a cobrir.</p>
<p><b>Pagar (call):</b> você coloca as fichas que faltam para acompanhar a aposta. Se a aposta é 10 e você já colocou 4 nesta rodada, paga mais 6.</p>
<p><b>Apostar / Aumentar (bet / raise):</b> você inicia uma aposta ou aumenta o valor que os outros precisam acompanhar. O campo “Total na rodada” inclui o que você já colocou nesta rodada: se já colocou 4 e escolhe total 10, coloca mais 6.</p>
<p><b>Todas as fichas (all-in):</b> você aposta tudo o que ainda tem. Não pode perder mais fichas do que colocou na mão. Se faltar saldo para acompanhar tudo, pode disputar apenas a parte do pote coberta pelas suas fichas; o restante é disputado separadamente.</p>
<h3>Cartas e etapas da mão</h3>
<p>Cada jogador recebe duas cartas só suas. Depois são abertas até cinco cartas no centro, que todos podem usar. A melhor combinação de cinco cartas vence; não é obrigatório usar suas duas cartas.</p>
<p><b>Pré-flop:</b> antes de abrir cartas no centro. <b>Flop:</b> primeiras três cartas. <b>Turn:</b> quarta carta. <b>River:</b> quinta carta. <b>Showdown:</b> comparação final das mãos de quem continuou.</p>
<p>As letras nas cartas são A = Ás, K = Rei, Q = Dama e J = Valete. O código T dos registros antigos significa 10. Naipes: ♠ espadas, ♥ copas, ♦ ouros, ♣ paus. Códigos antigos s/h/d/c correspondem a esses naipes.</p>
<h3>Força das combinações</h3>
<p>Da menor para a maior: carta alta; par (duas do mesmo valor); dois pares; trinca (três do mesmo valor); sequência (cinco valores seguidos); flush (cinco do mesmo naipe); full house (trinca e par); quadra (quatro iguais); straight flush (sequência do mesmo naipe).</p>
<p>Dois jogadores podem ter “par” e ainda assim um vencer: primeiro vale o valor do par, depois as cartas restantes mais altas, chamadas de desempate ou kickers. Só existe empate quando as melhores cinco cartas têm a mesma força. Os naipes não desempatarão.</p>
<h3>Apostas obrigatórias: blind menor e maior</h3>
<p>Antes de distribuir, dois jogadores colocam apostas obrigatórias para iniciar o pote. São chamadas small blind (menor, SB) e big blind (maior, BB). O botão (dealer, D) é uma marca que anda a cada mão e ajuda a definir quem coloca essas apostas e a ordem de jogar. Não significa que esse jogador recebe cartas melhores.</p>
<h3>Posição</h3>
<p>É sua vez de agir em relação aos outros jogadores. Agir depois permite observar o que os outros fizeram antes de decidir. Não é apenas o lugar desenhado na tela. Após as três primeiras cartas da mesa, começa o primeiro jogador ainda participando à esquerda do botão. Com só dois jogadores, o botão começa antes de abrir cartas; o outro começa depois.</p>
<h3>Mãos possíveis do adversário (range)</h3>
<p>Você não conhece as cartas escondidas do outro jogador. Um range é um conjunto de mãos que ele poderia ter: por exemplo, pares altos e Ás com Rei. É uma hipótese baseada no que observamos, não uma certeza nem acesso às cartas dele. O aplicativo ainda não calcula esses conjuntos automaticamente.</p>
<h3>Participação esperada no pote (equity)</h3>
<p>É a parte média do pote que uma mão receberia se as cartas restantes fossem abertas e as mãos comparadas, considerando vitórias e empates. Contra um adversário, ganhar metade das vezes e perder metade dá 50%. Empatar sempre e dividir em duas partes também dá 50%.</p>
<p>Depende das cartas que ainda podem sair e das mãos possíveis dos adversários. NÃO é a mesma coisa que a chance de melhorar sua combinação. O painel atual não calcula a equity das suas cartas; ele explica apenas o preço de pagar.</p>
<h3>Preço para continuar (pot odds)</h3>
<p>Exemplo: há 80 fichas no pote e custa 20 acompanhar. Depois de pagar, seriam 100. Você paga 20 para disputar 100: 20%. Sem novas apostas ou taxas, precisaria recuperar em média pelo menos 20% desse pote para compensar o pagamento. Isso não informa se suas cartas conseguem esse resultado.</p>
<h3>Taxa da mesa (rake)</h3>
<p>É uma parte do pote retirada como taxa. Neste simulador é opcional, fictícia e vem desligada por padrão. Se um pote tem 100 fichas e a taxa aplicável é 5, sobram 95 para os jogadores. “Sem taxa adicional” queria dizer que a conta simplificada não descontava nenhuma outra retirada. Agora o painel usa essa explicação em português.</p>
<h3>Limite que dois jogadores podem disputar (stack efetivo)</h3>
<p>Imagine que você tem 200 fichas e um adversário tem 60. Entre vocês dois, cada um só pode colocar em risco até 60: esse é o stack efetivo no início dessa disputa. Com vários jogadores, esse limite pode ser diferente para cada adversário e podem surgir potes separados.</p>
<h3>Como aprender com uma mão</h3>
<p>Receber fichas não é o mesmo que lucrar: parte delas pode ser o que você mesmo apostou ou uma devolução. Para ver o saldo, compare suas fichas antes e depois da mão. Uma decisão não se torna boa só porque ganhou, nem ruim só porque perdeu. Observe o preço de continuar e o que era possível saber na hora de decidir.</p>
'''
