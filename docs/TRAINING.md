# Treinamento — 0.3.0

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

Visão computacional, currículo avançado e comparação de ranges por equity permanecem pendentes na Fase 3.
