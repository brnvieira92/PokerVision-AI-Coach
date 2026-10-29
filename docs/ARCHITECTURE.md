# Arquitetura

## Plano e inspeção

O checkout inicial continha apenas `.git`. A Fase 1 criou o motor independente e a mesa jogável. Na Fase 2 foram preservados esse motor e os registros existentes; acrescentaram-se snapshots pré-ação, coach opcional, workers e migração de dados. A primeira entrega da Fase 3 acrescenta revisão visual, exercícios e métricas sem dependências pesadas. Interface didática e fórmulas continuam funcionando sem servidor de IA.

## Módulos e dependências

- `cards.py`: baralho e ranking lexicográfico exato de cinco a sete cartas.
- `engine.py`: `Table`/`Player`, regras de no-limit, sem GUI, banco ou IA.
- `math_engine.py`: fórmulas, Monte Carlo e resultados Pydantic, sem texto do coach.
- `bots.py`: projeção pública `Observation` + cartas próprias. Ações passam novamente pela validação do motor.
- `education.py`: vocabulário, guia, tradução de históricos antigos e lições básicas na mesa.
- `coach.py`: `DecisionSnapshot`, `DecisionAnalysis`, `DecisionRecord`, `LessonChoice` e `CoachReply`. PokerCoachService valida e organiza o catálogo de explicações. Snapshots têm apenas cartas do usuário, board e dados públicos anteriores à ação; não contêm vencedor, resultado ou cartas privadas alheias.
- `ollama.py`: HTTP local via stdlib, tags, chat, pull e unload. Sem credenciais ou downloads implícitos. Limites de resposta, timeout total e leitura cancelável. Respostas HTTP chunked são tratadas por HTTPResponse; o reader verifica cancelamento/timeout sem invalidar o buffer a cada pausa de rede.
- `resources.py`: HardwareProfiler com psutil/nvidia-smi e fallback sem GPU. ResourceManager serializa inferências e reduz o modo sob pouca RAM. Não altera configuração de servidor ou outros aplicativos.
- `workers.py`: tarefas Qt, sinais e CancelToken. BackgroundJobs admite uma operação do painel por vez; inferências também compartilham um bloqueio independente da GUI. Cancelamento não publica resposta parcial como concluída.
- `coach_panel.py`: configuração, diagnóstico, autorização de download, progresso, cancelamento, seleção/revisão de decisões e persistência de explicações. Resultados antigos são descartados quando o contexto muda ou a janela fecha.
- `storage.py`: SQLite com schema v4; sessões, mãos, preferências, explicações e exercise_attempts. Migração preserva dados v1/v2. Novos snapshots ficam no JSON das mãos; históricos antigos continuam legíveis.
- `ranges.py`: classes canônicas de duas cartas, matriz 13×13, contagem de combinações e conjuntos didáticos próprios.
- `training.py`: Exercise/Choice/Correction Pydantic, geradores, gabaritos, intervalo Wilson e recomendação por amostra/acertos recentes. Não depende da GUI, do LLM ou do banco.
- `review.py`: CardsCanvas e ReviewPanel; renderiza apenas os DecisionRecords, ignorando board final e cartas privadas alheias do payload da mão.
- `probability.py`: simulação de um adversário fixo/uniforme/condicionado a conjunto, remoção de cartas conhecidas, contagem distinta de vitórias e melhoria de categoria, exemplos de runouts e limite conservador de amostragem. Sem Qt ou LLM.
- `equity_ui.py`: entradas por seletores de cartas, presets, worker cancelável, barras e exemplos; usa identificação de geração para rejeitar resultados antigos após troca de cenário.
- `assistance.py`: projeção pública imutável da decisão, distribuição conjunta de mãos hipotéticas, modelo de continuação por pagamentos e comparação de cada pote elegível com devoluções/taxas/sobras. Não recebe Table no cálculo; apenas capture faz a projeção pública.
- `assistance_ui.py`: janela de estudo modal do simulador, worker cancelável, explicação das hipóteses e potes. Valida contexto antes de publicar resultado e libera a mesma decisão ao fechar.
- `study.py`: metas por assunto e comparação temporal de janelas móveis. Plano Pydantic serializado em preferences, sem migração adicional.
- `study_ui.py`: três blocos de prática persistidos; metas usam contagens posteriores à criação do plano.
- `training_ui.py`: exercícios, quadro editável e dashboard. A correção chama o repositório antes de atualizar a tela; repetir submissão não cria uma nova tentativa.
- `tournament.py`: controlador Sit & Go sem GUI, níveis por mãos, eliminações/classificação/premiação, checkpoints e cálculo ICM exato por subconjuntos.
- `tournament_bots.py`: wrapper heurístico para stacks curtos sobre observações autorizadas.
- `table_view.py`: desenho Felt extraído sem alterar regras, reutilizado em Cash Game e Sit & Go.
- `tournament_ui.py`: mesa e sessão SNG independentes, modos de treino, retomada e relatórios.
- `ui.py`: comandos, desenho QPainter, bot timer e coordenação. Captura a decisão antes de chamar o motor, registra apenas após uma ação válida e salva ao concluir a mão. Modos de treino são fixados ao aplicar uma sessão, evitando revelar dicas por mudança não aplicada do combo.

## Fluxo de decisão

GUI → snapshot público antes da ação → análise com pot odds, hipóteses/dados ausentes → coach opcional em worker → validação → renderização de texto verificado. A ação do jogador segue GUI → Table.act → validação/transição → DecisionRecord → snapshot da mão concluída → SQLite.

A probabilidade real de ganhar não é calculada pelo LLM. A resposta deve repetir identificação/fatos e selecionar tópicos válidos, sem campos extras ou texto livre. O app publica os textos do catálogo associados aos tópicos e seus próprios números. Essa escolha limita a flexibilidade do modelo e impede que uma resposta aparentemente plausível altere contas verificadas. Erros de serviço/schema/fatos acionam explicação determinística. Cancelamento é distinto de falha: encerra o pedido sem apresentar uma nova resposta como concluída.

Na Avaliação, nenhuma explicação por decisão é permitida enquanto uma sessão estiver aberta, mesmo entre mãos. “Finalizar sessão e revisar” encerra a sessão e libera snapshots. O resumo não usa resultado final para classificar decisões como boas/ruins e não atribui notas sem fundamento.

## Invariantes do motor preservadas

Estados: `finished → preflop → flop → turn → river → finished`. Fold de todos menos um termina em qualquer etapa. Sem decisões com fichas, completa-se o board. Há burn card por etapa. Aleatoriedade padrão sem semente; sementes opcionais reproduzem testes, sem ajustar distribuição em função do usuário.

Ordem circular; no heads-up o botão posta a aposta menor e age primeiro pré-flop, e o outro começa pós-flop. `current` guarda o preço, `increment` o último aumento completo e `acted` o preço da última ação de cada jogador. Aumentos incompletos só reabrem raise quando o acréscimo acumulado desde a última ação chega ao incremento completo. Não se aumenta sem oponente capaz de responder.

Contribuições totais e apostas de cada rodada são separadas. Níveis de contribuição criam potes independentes; quem desistiu contribui mas não disputa. Um nível com um único contribuinte é devolvido. Odd chips vão primeiro aos vencedores à esquerda do botão. Rake não incide sobre devoluções.

Após ações: stacks não negativos, cartas únicas, stacks + pote conservados. Após liquidação: stacks + rake conservados. Validação de ações ocorre antes de mutações; asserts são diagnósticos adicionais.

## Limites e extensão

ResourceManager usa limites conservadores: abaixo de 1,5 GB livres, sem LLM; abaixo de 3 GB, Equilibrado vira Econômico. Não reserva memória nem monitora continuamente. Só nvidia-smi expõe GPU/VRAM nesta versão; GPUs não NVIDIA podem aparecer como não detectadas. O modo CPU do provider e o fallback matemático permanecem disponíveis.

Ollama recebe contexto 2048, previsão máxima 384, temperatura 0.2, think=false e keep_alive=2m. Protocolos e erros são testados com servidor simulado; a validação com modelo real permanece pendente enquanto o serviço não estiver disponível e o modelo não tiver sido autorizado/instalado.

A Fase 3 já acrescenta exercícios e métricas sobre os registros pré-ação; já inclui laboratório de equity contra um range explícito; ainda faltam análise de valor de apostas contra ranges, visão offline e treinamento estratégico mais amplo. Torneios devem coordenar Table sem introduzir Qt no motor; antes, blinds progressivos, seating e ICM terão testes próprios. Não inferir snapshots históricos completos a partir de strings antigas, nem usar informações futuras para julgar decisões.


## Exercícios e progresso

ExerciseFactory usa Random injetável para testes e UUID independente para cada exercício. Comparações usam o avaliador exato existente; preço usa pot_odds. O banco guarda o enunciado/alternativas/gabarito completos, a escolha e o resultado, permitindo auditar tentativas sem depender de uma versão futura do gerador. exercise_id é chave primária e bloqueia recontagem ou troca de resposta depois da primeira submissão. Há um perfil local de treino, sem contas externas.

A recomendação primeiro cobre amostras inferiores a três respostas por assunto; depois usa (acertos recentes + 1)/(respostas recentes + 2), com janela de vinte por assunto. O dashboard mostra contagens de todo o histórico e faixa Wilson com z=1.96; a faixa é apenas ilustrativa sob exercícios repetidos/correlacionados. Notas estratégicas e Tournament Readiness Score não são calculados.

O quadro de mãos agrupa seis combinações por par, quatro por classe do mesmo naipe e doze por classe de naipes diferentes. As 169 classes cobrem as 1326 combinações sem cartas conhecidas. O quadro em si mantém a contagem anterior a cartas conhecidas; o laboratório expande a seleção e remove blockers antes de calcular equity. As seleções são exemplos pedagógicos próprios, sem frequências mistas ou calibração por solver.


## Simulação e comparação temporal (0.4)

O laboratório usa somente as entradas visíveis escolhidas pelo usuário. Contra um range, primeiro sorteia uniformemente uma combinação legal de duas cartas e depois as comunitárias faltantes dentre as restantes. Contra mãos aleatórias, sorteia o adversário e as comunitárias sem reposição. Cada repetição inicia do mesmo cenário, com semente reprodutível. As contagens somam a amostra e a equity deve ser exatamente (vitórias + empates/2)/N. Melhorar categoria não é usado como substituto da equity.

Para o erro de amostragem de participações em [0,1], usa raio sqrt(log(40)/(2N)), derivado da desigualdade bilateral de Hoeffding para 95%. O intervalo é limitado a [0,1] e não colapsa artificialmente para certeza após uma amostra só de vitórias. Não inclui incerteza de modelagem, comportamento de apostas ou adversários adicionais. O worker verifica cancelamento em cada repetição e emite progresso a cada cinquenta. A UI descarta resultados de cenário alterado ou avaliação em andamento.

A comparação de períodos usa timestamps UTC persistidos e janelas móveis de duração exata: período atual inclui o início da janela; a janela anterior termina antes desse início, sem sobreposição. Registros futuros são excluídos. Mostra mudança de taxa em pontos percentuais apenas quando ambas as amostras são não vazias. Diferentes perguntas e amostras pequenas impedem interpretar a diferença como prova de evolução estratégica.

Os planos usam contagem inicial por assunto e meta de cinco novas respostas; criar novo plano não apaga tentativas. O plano não avalia qualidade de decisões de cash game e completar uma meta de prática não significa dominar o assunto.


## Jogo assistido (0.5)

A UI só abre a ajuda quando o usuário é o ator atual em Aprendizagem. Captura AssistedScenario e DecisionAnalysis antes de pausar. AssistedScenario contém a mão do usuário, board aberto, nomes/saldos/apostas/contribuições/desistências públicos, botão e configuração de taxa. Cada PublicPlayer proíbe campos extras; não há hole de adversário, objeto Table, deck ou resultado futuro na entrada do worker. Testes alteram cartas privadas e a ordem do baralho real sem alterar a simulação assistida.

Enquanto assistance_paused é verdadeiro, perform, bot_step, configure e new_hand não mudam a partida. A janela usa Qt.WindowModal e os controles de ação são desabilitados. Fechar/aceitar/rejeitar cancela o token, invalida a janela e retoma a mesma decisão. Publicação exige mesmo cenário público, ID correspondente, janela ativa e Aprendizagem; retorno atrasado não registra uma análise concluída.

Projeção terminal: todos os não desistentes completam o preço atual até o saldo disponível; nenhuma aposta ou desistência adicional ocorre. Contribuições criam níveis, participantes elegíveis e devolução de nível não coberto. Taxa por pote e teto são aplicados como em Table._settle, sob a hipótese de flop/showdown. A média recebida é calculada em fichas inteiras por pote, com odd chips à esquerda do botão. Não é EV de raise nem recomendação ótima.

A equity contra todos é a média de 1/k quando o usuário empata entre k melhores mãos, ou zero quando perde. Com stacks diferentes ela não equivale à participação monetária no pote inteiro. A tabela mostra estimativa de recebimento por pote com faixa Hoeffding escalada pelo máximo de fichas daquele pote; devoluções e ausência de elegibilidade têm valor determinístico. Cada intervalo é individual; não há alegação de cobertura conjunta de todas as faixas.

Com range comum, expande combinações legais sem cartas conhecidas e sorteia uma combinação para cada adversário independentemente. Rejeita a atribuição inteira se houver colisão; apenas ressortear a mão colidente enviesaria a distribuição conjunta. Há verificação de cartas suficientes, limite de tentativas e cancelamento, sem fallback silencioso para outro modelo. Se não consegue sortear a hipótese, pede conjunto mais amplo ou uniforme.

Repository.save aceita assistance opcional no JSON existente, sem nova migração. Relatórios concluídos são vinculados ao DecisionSnapshot.id reutilizado no registro da ação real; só a última análise por decisão é guardada. O histórico marca uso de assistência, sem misturá-lo com acertos de exercícios ou julgar a decisão pelo resultado posterior.


## Primeira entrega Sit & Go (0.6)

Tournament coordena uma instância de Table com rake zero. Conserva o total inicial de fichas; não expõe operação de recomposição. Define blinds antes de cada mão pelo número de mãos já concluídas. Uma mão concluída automaticamente ao postar blinds também é processada, evitando perder eliminações em heads-up all-in.

Eliminações são confirmadas somente após liquidação. Agrupa quem ficou sem fichas por stack no início da mão, em ordem decrescente. Empates ocupam um intervalo de posições e dividem exatamente a soma dos respectivos prêmios com Fraction. A soma dos prêmios finais deve igualar o fundo fictício. Controlador e ICM aceitam até nove; a primeira UI é seis jogadores.

ICM remove sucessivamente o próximo colocado com probabilidade stack/total restante. Memoização por máscara de participantes evita enumerar permutações repetidas. Não inclui habilidade, posição, blinds futuros ou respostas de adversários. A UI não calcula ICM durante uma mão, nem o publica durante um torneio de Avaliação ativo.

Schema v4 adiciona tournaments(id,created,updated,state,payload). save_tournament_hand grava mão, contexto de modalidade, decisões e checkpoint numa única transação. Falha no checkpoint reverte também o INSERT da mão; teste injeta falha SQL para verificar isso. Checkpoint inclui config, stacks, botão, grupos, participantes, número de mãos e session_id, sem baralho futuro. Restore valida conservação e posições. A retomada é exclusivamente entre mãos e não preserva o estado aleatório interno dos bots.

TournamentPanel tem mesa própria, timer que só avança quando visível e aceleração após eliminação. Cash Game fica bloqueado enquanto houver SNG ativo. Encerrar a janela durante uma mão SNG avisa do descarte daquela mão; o último checkpoint continua retomável. Abandono é permitido entre mãos e não inventa posições finais para quem restou. A mesa desenhada foi extraída para table_view sem duplicar motor de regras.

As pendências da Fase 3 estão em PENDING_PHASE3.md; completar a Fase 4 ainda requer mesa de nove, antes, progressão por relógio e treino de decisões push/fold/ICM sob hipóteses explícitas.
