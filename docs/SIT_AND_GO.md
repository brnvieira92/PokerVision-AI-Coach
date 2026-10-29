# Sit & Go — primeira entrega da Fase 4 (0.6.0)

## Jogar

1. Termine a mão de Cash Game. Se a sessão estiver em Avaliação, finalize-a pelo Coach IA.
2. Abra **Jogar Sit & Go** no menu lateral. Esta primeira mesa tem seis jogadores.
3. Configure fichas iniciais, aposta maior inicial, mãos por nível, inscrição fictícia, distribuição dos prêmios e modo de treino.
4. Clique em **Iniciar novo torneio**. Você e cinco bots começam com stacks iguais. Os bots agem em sequência até sua vez; os botões são os mesmos do Cash Game.
5. Ao terminar cada mão, clique em **Próxima mão**. Os blinds dobram a cada quantidade configurada de mãos, até um teto de duas vezes o total de fichas. A aposta menor é metade da maior, arredondada para baixo, no mínimo uma ficha. A progressão é por mãos, não por tempo de relógio.
6. Consulte **Aprender** e **Classificação / ICM** nas abas à direita. Em Avaliação, dicas e estimativas ICM ficam ocultas até encerrar o torneio.
7. Se for eliminado, você pode continuar observando ou clicar em **Simular restante após eliminação**. A aceleração para quando você sai da página ou quando o torneio termina. **Parar aceleração** devolve o ritmo normal.
8. A classificação final aparece automaticamente quando há um campeão. As mãos concluídas também aparecem em **Analisar mãos**, com a identificação Sit & Go.

Não há recomposição, recompra, antes, entrada tardia ou rake nas mãos do torneio. A inscrição e a premiação são pontos fictícios; não se usa dinheiro nem conta externa. Os parâmetros ficam fixos depois de iniciar.

## Retomar e encerrar

Abaixo da mesa, escolha um torneio salvo e clique em **Abrir / retomar torneio salvo**. O checkpoint guarda stacks, participantes, botão, nível por quantidade de mãos, classificação e sessão. Um torneio concluído pode ser aberto para consultar o relatório.

Cada mão e seu checkpoint são gravados na mesma transação SQLite. Se o aplicativo fechar durante uma mão, essa mão é descartada; ao voltar, retoma-se o último intervalo salvo, sem duplicar a mão já persistida. O fechamento avisa quando há mão incompleta. Não há retomada de uma decisão no meio da mão. As decisões aleatórias dos bots após retomar podem variar; não se promete reproduzir sua sequência aleatória anterior.

**Abandonar entre mãos** registra o encerramento antecipado. Não inventa um campeão nem paga prêmios finais aos participantes restantes. É possível retomar outros torneios salvos ou iniciar Cash Game depois disso. Cash Game e Sit & Go não podem ficar em andamento ao mesmo tempo. Trocar de página pausa o avanço dos bots do torneio; voltar permite continuar.

## Classificação e prêmios

O fundo fictício é seis vezes a inscrição. As opções são dois premiados (60/40) ou três (50/30/20). Quando a divisão percentual não gera pontos inteiros, os restos são distribuídos pelas maiores frações, com prioridade à melhor posição em caso de igualdade. O total dos prêmios é conservado.

Uma eliminação só é confirmada após liquidar os potes. Se vários forem eliminados na mesma mão, quem começou a mão com mais fichas recebe a posição melhor. Com fichas iniciais iguais, as posições ficam empatadas e os prêmios correspondentes são divididos igualmente. Internamente, essa divisão usa frações exatas; a interface arredonda para duas casas. Os participantes ainda na disputa não recebem classificação final antecipada.

Referência conceitual para eliminações simultâneas: [PokerStars, mecânica de torneios](https://www.pokerstars.com/help/articles/rules-table-master/213164/). O simulador não se conecta a essa plataforma e não reproduz uma estrutura de torneio específica.

A regra de botão continua a do motor próprio: avança para o próximo participante ativo. Não reproduz a variante de botão morto de determinados regulamentos. Heads-up usa o botão como aposta menor, primeiro pré-flop e último pós-flop. As posições vazias continuam na representação da mesa.

## ICM didático

Entre mãos, o relatório compara uma divisão simplesmente proporcional às fichas com o valor ICM dos participantes restantes. O ICM atribui a chance da próxima colocação proporcionalmente ao stack, retira aquele jogador e repete o cálculo para os prêmios seguintes. O algoritmo é exato por subconjuntos para até nove stacks positivos; não é Monte Carlo.

Exemplos de referência cobertos por testes:

- Dois stacks iguais, prêmios 70/30: valores 50/50.
- Stacks 90/10, prêmios 70/30: valores 66/34, não 90/10.
- Apenas um prêmio: o valor é proporcional às fichas.
- Três stacks iguais, prêmios 50/30/20: cada um tem valor 100/3.

O valor é uma expectativa segundo o modelo, não o prêmio já garantido nem uma previsão da posição final. Ignora diferenças de habilidade, posição, próximos blinds, acordos e bounties. Não calcula se um all-in tem melhor EV de premiação do que desistir. A comparação está disponível somente entre mãos na Aprendizagem ou após encerrar a Avaliação.

Referência conceitual: [ICMIZER, definição do modelo](https://support.icmpoker.com/en/articles/3699969-what-is-the-icm-model).

## Adversários e limites desta entrega

Os bots continuam heurísticos e recebem apenas as próprias cartas e informações públicas. Com poucas fichas, usam uma regra simples de colocar tudo/desistir baseada em pares, cartas altas e naipes, respeitando as ações legais. Não resolvem ICM, Nash ou GTO, não ajustam ranges de forma calibrada à bolha e não alteram a distribuição de cartas para favorecer o usuário.

O jogo assistido com equity continua exclusivo do Cash Game nesta versão. Não se aplica automaticamente a um torneio, onde equity de showdown, fichas e valor esperado de prêmio são medidas diferentes.

A interface inicial suporta seis jogadores. O controlador e o ICM têm testes com até nove, mas a mesa de nove jogadores, antes, níveis por relógio, estruturas avançadas, exercícios push/fold e avaliação de decisões com ICM ficam para as próximas entregas da Fase 4. MTT continua na Fase 5.
