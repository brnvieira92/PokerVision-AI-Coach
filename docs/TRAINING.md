# Treinamento — 0.5.0

## Gabaritos

- Combinações: sorteia nove cartas sem repetição, duas para cada jogador e cinco comunitárias. Compara evaluate(7 cartas). A correção apresenta as melhores cinco em ordem legível e explica se vence pela categoria ou pelo primeiro valor de desempate diferente. Empate usa igualdade das tuplas de ranking; naipe não desempata.
- Preço: call/(pot+call), em porcentagem arredondada para uma casa. Supõe ausência de apostas futuras/taxas; não estima equity. Valores da revisão só entram quando DecisionAnalysis indica conta simples aplicável.
- Apostas: diferença entre total exigido e fichas já colocadas na rodada. O saldo é implicitamente suficiente nesse exercício aritmético; all-ins não são avaliados como se fossem calls comuns.
- Posição: ordem pós-flop com todos ainda na mão em seis jogadores e exceção heads-up antes das cartas da mesa. Não avalia decisões de apostas.
- Mãos iniciais: canonicaliza duas cartas para par, suited ou offsuit. T é a abreviação padrão do dez no quadro; as cartas desenhadas mostram 10 e a legenda ensina a notação.

## Persistência e amostra

Cada exercício tem UUID e sua primeira resposta é registrada com o exercício completo. Submeter a mesma resposta novamente é idempotente; tentar trocar a resposta de um exercício registrado é rejeitado. Uma nova pergunta recebe novo ID e conta como nova tentativa, mesmo se o cenário coincidir. Por isso, a proporção de acertos não mede diretamente desempenho em situações independentes ou inéditas.

A ordem cronológica é a ordem de inserção no banco. A recomendação cobre os assuntos com menos de três respostas primeiro, começando pelo menos praticado. Quando todos têm pelo menos três, prioriza a menor taxa suavizada (corretas + 1)/(total + 2) nas vinte respostas mais recentes de cada assunto. Essa regra é documentada e determinística; não usa lucro fictício nem julgamentos livres da IA.

O dashboard mostra acertos/total de toda a amostra e o intervalo Wilson bilateral de 95%, com z=1.96. Zero respostas significa ausência de estimativa, não zero habilidade. A dependência entre perguntas e a seleção adaptativa limitam a interpretação estatística. Não se converte o intervalo em promessa de desempenho em jogos ou torneios.

Referência da fórmula: [NIST, intervalos para proporções](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm).

## Ranges didáticos

Os três exemplos de conjuntos foram criados no projeto. Não copiam uma tabela de uma sala nem representam solução GTO. A posição tem explicação separada: mudar o assento no painel não altera os exemplos nem gera uma ação recomendada. A seleção se aplica a todas as combinações de cada classe, sem cartas removidas: par = 6, mesmo naipe = 4, naipes diferentes = 12. O teste enumera todas as combinações do baralho e confere esses pesos.

Como referência conceitual de posição e seleção de mãos: [PokerStars Learn, mãos iniciais](https://www.pokerstars.com/poker/learn/lesson/poker-starting-hands/). Os números dos exemplos próprios não são atribuídos a essa fonte.

## Revisão e limites

O revisor lê apenas decisions[].analysis.decision; não usa payload.board final, awards ou cartas de outros jogadores para ensinar uma decisão anterior. A ação efetivamente escolhida aparece como registro, sem nota estratégica. Não há animação de todas as ações ou reconstrução de estados ausentes em mãos antigas.

A Avaliação bloqueia exercícios, ranges, progresso com perguntas anteriores e revisão até o encerramento da sessão. Na Aprendizagem, a revisão exige mão concluída; exercícios separados podem ser feitos sem abrir mesa. O guia básico de termos continua disponível.

Visão computacional e currículo estratégico avançado permanecem pendentes. A comparação de equity contra um range escolhido está disponível no laboratório, sem avaliar valor de apostas ou indicar ação ótima.


## Novos cenários

- Primeira aposta: posição inicial ou botão, seis jogadores, 100 BB, ninguém entrou. O enunciado declara um conjunto próprio e uma regra aumentar/desistir. Corrige aderência à regra, não uma solução GTO. Casos incluídos/excluídos são balanceados no gerador; isso não muda a distribuição de cartas da mesa jogável.
- Blind maior: aposta obrigatória já colocada, um aumento e as demais pessoas desistiram. Calcula custo incremental e explica preço, sem afirmar que defender é a melhor jogada.
- Flush: quatro cartas conhecidas de um naipe no flop e nenhuma carta adversária conhecida; 9 entre 47 completam o naipe na próxima carta. Não confundir essa probabilidade com vencer ou com as duas cartas restantes combinadas.

## Equity e melhoria de categoria

Cada simulação compara exatamente as melhores cinco cartas de cada jogador. Empate de dois jogadores vale meio pote. A categoria final só conta como melhoria quando é estritamente superior à inicial; melhora de kicker não conta. Ao explorar runouts, a UI rotula todos como hipóteses sorteadas e nunca importa cartas privadas alheias de uma mão salva.

Um adversário de range é uniforme entre combinações físicas legais depois de remover cartas conhecidas. Isso preserva pesos 6/4/12 antes de blockers, em vez de sortear classes como se tivessem o mesmo peso. O laboratório é de um adversário; importar uma decisão com mais jogadores não preserva o número de oponentes, e essa simplificação é mostrada explicitamente.

Faixa de amostragem: média das participações em [0,1], com raio sqrt(log(40)/(2N)) a partir da desigualdade de Hoeffding, limitado a [0,1]. Assume sorteios independentes sob o modelo; não valida o modelo de adversário. Referência matemática: [notas de probabilidade da CMU, desigualdade de Hoeffding](https://www.math.cmu.edu/~gautam/c/2026-425/notes/mgf.html).

## Plano e períodos

O plano seleciona três assuntos, priorizando menos de três respostas e depois o menor acerto suavizado nas últimas vinte. Cada bloco pede cinco respostas novas em relação à contagem salva na criação do plano. A meta é de prática e não de acertos; resultados continuam separados no dashboard. Regenerar o plano muda somente metas e contagens iniciais.

O filtro de 7/30 dias usa janelas móveis e compara uma janela anterior com duração igual, sem sobreposição. Sem observações em qualquer lado, a mudança fica sem comparação, não zero. A diferença é em pontos percentuais, sem atribuição causal. A recomendação permanece baseada no histórico de treino completo para evitar mudar o currículo por um simples filtro de visualização.


## Jogo assistido

Ajuda exclusiva da mesa simulada em Aprendizagem, com pausa explícita antes da ação. Faz comparação contra todos os adversários ainda participando, sem consultar suas cartas privadas. Usa mãos uniformes ou um mesmo conjunto manual para todos, condicionado a cartas distintas. Exemplos mostram apenas boards possíveis, não as mãos adversárias reais ou sorteadas.

As estimativas são condicionadas à política declarada de completar o preço atual sem raises/folds nem apostas futuras. Potes são formados a partir dessas contribuições hipotéticas; não devem ser confundidos com as fichas que já estavam no centro. All-ins limitam elegibilidade e podem criar vários potes. A equity contra todos e o recebimento médio de cada pote são medidas distintas. Nenhuma delas, sem hipótese de resposta às alternativas, prova a melhor ação.

Empate multiway vale 1/k para equity. Recebimento por pote usa divisão inteira e ordem das sobras do motor, incluindo taxa e devoluções. A análise não usa resultado futuro para julgar a ação escolhida e não atribui uma nota de exercício a uma mão assistida.
